"""Tests for GDPR field-level redaction.

REQ-USR-01 marks DNI and IBAN as private, but every listing returned them — plus
home address and date of birth — to anyone with users:read. These pin down who
sees what.
"""

import pytest

from app.services.user_visibility import (
    CONTACT_FIELDS,
    PUBLIC_FIELDS,
    SENSITIVE_FIELDS,
    UserVisibility,
)


class FakeUser:
    """Minimal stand-in with every field UserResponse reads."""

    def __init__(self, user_id=1):
        from datetime import date, datetime

        self.id = user_id
        self.name = "Ana"
        self.surname = "García"
        self.photo = "photo.png"
        self.job_position = "Coordinadora"
        self.is_active = True
        self.must_change_password = False
        self.created_at = datetime(2026, 1, 1)
        self.email = "ana@example.org"
        self.phone = "600000000"
        self.size = "M"
        self.hobbies = "Senderismo"
        self.dni = "12345678Z"
        self.iban = "ES9121000418450200051332"
        self.address = "Calle Mayor 1"
        self.birthdate = date(1990, 5, 17)


def test_tiers_do_not_overlap():
    assert not PUBLIC_FIELDS & CONTACT_FIELDS
    assert not PUBLIC_FIELDS & SENSITIVE_FIELDS
    assert not CONTACT_FIELDS & SENSITIVE_FIELDS


def test_sensitive_tier_covers_the_fields_the_srs_calls_private():
    assert {"dni", "iban"} <= SENSITIVE_FIELDS


def test_plain_viewer_sees_only_public_fields():
    result = UserVisibility(can_read_contact=False, can_read_sensitive=False).serialize(
        FakeUser(1), viewer_id=99
    )

    assert result.name == "Ana"
    assert result.surname == "García"
    assert result.is_active is True
    for field in CONTACT_FIELDS | SENSITIVE_FIELDS:
        assert getattr(result, field) is None, f"{field} leaked to a plain viewer"


def test_contact_permission_reveals_contact_but_not_sensitive():
    result = UserVisibility(can_read_contact=True, can_read_sensitive=False).serialize(
        FakeUser(1), viewer_id=99
    )

    assert result.email == "ana@example.org"
    assert result.phone == "600000000"
    for field in SENSITIVE_FIELDS:
        assert getattr(result, field) is None, f"{field} leaked without read_sensitive"


def test_sensitive_permission_reveals_everything():
    result = UserVisibility(can_read_contact=True, can_read_sensitive=True).serialize(
        FakeUser(1), viewer_id=99
    )

    assert result.dni == "12345678Z"
    assert result.iban == "ES9121000418450200051332"
    assert result.address == "Calle Mayor 1"
    assert result.birthdate is not None


def test_sensitive_without_contact_is_still_honoured_independently():
    """The tiers are separate grants, not a ladder."""
    result = UserVisibility(can_read_contact=False, can_read_sensitive=True).serialize(
        FakeUser(1), viewer_id=99
    )

    assert result.dni == "12345678Z"
    assert result.email is None


def test_subject_always_sees_their_own_record_in_full():
    result = UserVisibility(can_read_contact=False, can_read_sensitive=False).serialize(
        FakeUser(7), viewer_id=7
    )

    assert result.dni == "12345678Z"
    assert result.iban == "ES9121000418450200051332"
    assert result.email == "ana@example.org"


def test_no_viewer_id_is_treated_as_not_the_subject():
    """Guards against an unauthenticated path accidentally getting full data."""
    result = UserVisibility(can_read_contact=False, can_read_sensitive=False).serialize(
        FakeUser(1), viewer_id=None
    )

    assert result.dni is None
    assert result.iban is None


@pytest.mark.parametrize("field", sorted(SENSITIVE_FIELDS))
def test_every_sensitive_field_is_redacted(field):
    result = UserVisibility(can_read_contact=True, can_read_sensitive=False).serialize(
        FakeUser(1), viewer_id=99
    )
    assert getattr(result, field) is None


def test_bulk_upload_csv_column_is_nullable():
    """The uploaded file must be discardable once the job finishes.

    It carries a `password` column in clear text plus the DNI, address and IBAN
    of everyone in it; keeping it after processing serves no purpose and is
    hard to defend under storage limitation.
    """
    from app.models.bulk_upload_job_model import BulkUploadJob

    column = BulkUploadJob.__table__.c.csv_content
    assert column.nullable, (
        "csv_content is NOT NULL, so the credentials in the uploaded file "
        "cannot be discarded after the job completes"
    )


def test_failed_rows_survive_the_csv_being_discarded():
    """Discarding the uploaded file must not take the failure report with it.

    The job records each failed row — its number, the error and the row's own
    data — in `errors`, which is what the UI renders. Nothing re-reads
    csv_content after processing, so clearing it leaves the report intact.

    This pins the contract: if the failure record ever stops carrying the row
    data, purging the CSV would start losing information.
    """
    import inspect

    from app.services import user_service

    source = inspect.getsource(user_service.process_bulk_upload_job)

    # The failure record must keep the row's data, not just a row number.
    assert '"data": {k: v for k, v in row.items() if k != "password"}' in source, (
        "failed rows no longer record their data; discarding the CSV would now "
        "lose the detail behind each failure"
    )
    # And it must keep excluding the password.
    assert 'k != "password"' in source, (
        "the failure record no longer strips the password column"
    )
    # Nothing may read csv_content after it is cleared.
    after_clear = source.split("job.csv_content = None", 1)[-1]
    assert "csv_content" not in after_clear.replace("csv_content = None", ""), (
        "something reads csv_content after it is discarded"
    )


def test_every_model_reaches_the_metadata():
    """A model that is never imported is invisible to everything.

    MembershipRequest defined a table but was not imported in
    app/models/__init__.py, so it never reached Base.metadata. create_all did
    not build it for the test-suite, autogenerate could not see it, and no
    migration ever created it — self-registration failed with a 500 against
    any database built from migrations.

    The drift check cannot catch this: it compares the metadata against the
    database, and an unregistered model is absent from both.
    """
    import pathlib
    import re

    import app.models  # noqa: F401  — the import under test
    from app.database.database import Base

    registered = {table.name for table in Base.metadata.tables.values()}
    models_dir = pathlib.Path(__file__).resolve().parent.parent / "models"

    orphans = []
    for path in sorted(models_dir.glob("*_model.py")):
        for match in re.finditer(r'__tablename__\s*=\s*["\'](\w+)["\']', path.read_text()):
            if match.group(1) not in registered:
                orphans.append(f"{path.name} declares '{match.group(1)}'")

    assert orphans == [], (
        "these models never reach Base.metadata, so no migration will create "
        "their tables: " + "; ".join(orphans)
    )
