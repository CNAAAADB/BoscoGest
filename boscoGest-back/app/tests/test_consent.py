"""Tests for the GDPR data-processing consent.

Two halves: members accepting the clause in force, and superadmins authoring
versions of it.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.consent_clause_model import ConsentClause
from app.services.consent_service import (
    CONSENT_TEXT,
    FALLBACK_VERSION,
    ConsentService,
)


@pytest.fixture
def service(db_session):
    return ConsentService(db_session)


@pytest.fixture
def published_clause(db_session):
    """The clause in force. Seeded by migration in a real database."""
    clause = ConsentClause(
        version="1.0",
        text=CONSENT_TEXT,
        is_published=True,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(clause)
    db_session.commit()
    return clause


# ── Accepting ───────────────────────────────────────────────────────────────


def test_new_user_has_not_consented(service, test_user, published_clause):
    status = service.get_status(test_user)

    assert status.accepted is False
    assert status.accepted_at is None
    assert status.current_version == "1.0"
    # The clause travels with the answer so the client shows exactly what is
    # being agreed to, rather than a copy that could drift.
    assert status.text == CONSENT_TEXT


def test_accepting_records_version_and_timestamp(service, test_user, published_clause):
    before = datetime.now(timezone.utc) - timedelta(seconds=1)

    status = service.accept(test_user, "1.0")

    assert status.accepted is True
    assert status.accepted_version == "1.0"
    accepted_at = status.accepted_at
    assert accepted_at is not None
    if accepted_at.tzinfo is None:
        accepted_at = accepted_at.replace(tzinfo=timezone.utc)
    assert accepted_at >= before
    assert status.text is None


def test_stale_version_is_rejected(service, test_user, published_clause):
    """A client holding an old copy must not record consent for it."""
    with pytest.raises(HTTPException) as exc:
        service.accept(test_user, "0.1")

    assert exc.value.status_code == 409
    assert "out of date" in exc.value.detail


def test_publishing_a_new_version_invalidates_earlier_consent(
    service, test_user, published_clause, db_session
):
    """The point of versioning: changed terms have to be agreed to again."""
    service.accept(test_user, "1.0")
    assert service.get_status(test_user).accepted is True

    new_clause = service.create_clause(
        version="2.0", text="Texto revisado", author=test_user, publish=True
    )

    status = service.get_status(test_user)
    assert status.accepted is False
    assert status.accepted_version == "1.0"
    assert status.current_version == "2.0"
    assert status.text == "Texto revisado"
    assert new_clause.is_published is True


def test_falls_back_to_the_builtin_text_when_nothing_is_published(service, test_user):
    """A database with no published row must not leave members unable to consent."""
    status = service.get_status(test_user)

    assert status.current_version == FALLBACK_VERSION
    assert status.text == CONSENT_TEXT


# ── Authoring ───────────────────────────────────────────────────────────────


def test_creating_a_draft_does_not_change_the_clause_in_force(
    service, test_user, published_clause
):
    draft = service.create_clause(
        version="2.0", text="Borrador", author=test_user, publish=False
    )

    assert draft.is_published is False
    assert draft.published_at is None
    assert service.get_published_clause().version == "1.0"


def test_publishing_stands_down_the_previous_version(
    service, test_user, published_clause, db_session
):
    """A partial unique index allows only one published row."""
    draft = service.create_clause(
        version="2.0", text="Nuevo", author=test_user, publish=False
    )
    service.publish_clause(draft.id)

    db_session.refresh(published_clause)
    assert published_clause.is_published is False
    assert service.get_published_clause().version == "2.0"


def test_published_clauses_cannot_be_edited(service, test_user, published_clause):
    """Rewriting accepted text would destroy the record of what was agreed to."""
    with pytest.raises(HTTPException) as exc:
        service.update_draft(published_clause.id, "texto alterado")

    assert exc.value.status_code == 409
    assert "immutable" in exc.value.detail


def test_drafts_can_be_edited(service, test_user, published_clause):
    draft = service.create_clause(
        version="2.0", text="Primera redacción", author=test_user
    )

    updated = service.update_draft(draft.id, "Segunda redacción")

    assert updated.text == "Segunda redacción"


def test_duplicate_versions_are_rejected(service, test_user, published_clause):
    with pytest.raises(HTTPException) as exc:
        service.create_clause(version="1.0", text="Otro texto", author=test_user)

    assert exc.value.status_code == 409
    assert "already exists" in exc.value.detail


def test_blank_text_is_rejected(service, test_user, published_clause):
    with pytest.raises(HTTPException) as exc:
        service.create_clause(version="2.0", text="   ", author=test_user)

    assert exc.value.status_code == 422


def test_the_clause_in_force_cannot_be_deleted(service, published_clause):
    with pytest.raises(HTTPException) as exc:
        service.delete_draft(published_clause.id)

    assert exc.value.status_code == 409


def test_a_previously_published_version_cannot_be_deleted(
    service, test_user, published_clause, db_session
):
    """Somebody may have accepted it; the record has to survive."""
    draft = service.create_clause(version="2.0", text="Nuevo", author=test_user)
    service.publish_clause(draft.id)
    # 1.0 is now stood down but was published in the past.
    db_session.refresh(published_clause)

    with pytest.raises(HTTPException) as exc:
        service.delete_draft(published_clause.id)

    assert exc.value.status_code == 409
    assert "accepted" in exc.value.detail


def test_never_published_drafts_can_be_discarded(service, test_user, published_clause):
    draft = service.create_clause(version="2.0", text="Descartable", author=test_user)

    service.delete_draft(draft.id)

    assert all(c.version != "2.0" for c in service.list_clauses())


def test_pending_count_tracks_who_still_owes_consent(
    service, test_user, published_clause
):
    assert service.pending_acceptance_count("1.0") == 1

    service.accept(test_user, "1.0")

    assert service.pending_acceptance_count("1.0") == 0
    # Publishing new terms puts everyone back in the pending column.
    assert service.pending_acceptance_count("2.0") == 1


def test_versions_are_listed_newest_first(service, test_user, published_clause):
    service.create_clause(version="2.0", text="Nuevo", author=test_user)

    versions = [c.version for c in service.list_clauses()]

    assert versions[0] == "2.0"


def test_builtin_text_covers_the_required_gdpr_points():
    """Article 13 requires the data subject be told these things."""
    for heading in ("Responsable", "Finalidad", "Legitimación", "Conservación", "Derechos"):
        assert heading in CONSENT_TEXT
    assert "Agencia Española de Protección de Datos" in CONSENT_TEXT
