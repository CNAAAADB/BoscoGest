"""Authoring and publishing the GDPR data-processing clause.

Separate from the member-facing endpoints on /users/me/consent: this is the
superadmin side, gated behind consent:manage, because the clause is the legal
basis for processing every member's data across the whole platform.
"""

from typing import List

from fastapi import APIRouter, Depends, Response, status

from app.models.user_model import User
from app.schemas.user import (
    ConsentClauseCreate,
    ConsentClauseResponse,
    ConsentClauseUpdate,
)
from app.services.consent_service import ConsentService
from app.utils.auth import get_sync_db, require_permission

consent_router = APIRouter(prefix="/consent-clauses", tags=["GDPR Consent"])


@consent_router.get("", response_model=List[ConsentClauseResponse])
def list_clauses(
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """Every version, newest first — the audit trail of what was in force when."""
    return ConsentService(db).list_clauses()


@consent_router.get("/pending-count")
def pending_acceptance_count(
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """How many active members have not yet accepted the clause in force.

    Publishing a new version resets this to nearly everyone, so it is worth
    showing before and after.
    """
    service = ConsentService(db)
    version, _ = service._current_version_and_text()
    return {
        "current_version": version,
        "pending": service.pending_acceptance_count(version),
    }


@consent_router.post("", response_model=ConsentClauseResponse, status_code=status.HTTP_201_CREATED)
def create_clause(
    payload: ConsentClauseCreate,
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """Create a new version, optionally publishing it straight away."""
    return ConsentService(db).create_clause(
        version=payload.version,
        text=payload.text,
        author=current_user,
        publish=payload.publish,
    )


@consent_router.put("/{clause_id}", response_model=ConsentClauseResponse)
def update_draft(
    clause_id: int,
    payload: ConsentClauseUpdate,
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """Edit a draft. Published versions are immutable and answer 409."""
    return ConsentService(db).update_draft(clause_id, payload.text)


@consent_router.post("/{clause_id}/publish", response_model=ConsentClauseResponse)
def publish_clause(
    clause_id: int,
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """Put this version in force. Every member reaccepts on their next login."""
    return ConsentService(db).publish_clause(clause_id)


@consent_router.delete("/{clause_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    clause_id: int,
    db=Depends(get_sync_db),
    current_user: User = Depends(require_permission("consent", "manage")),
):
    """Discard a draft that was never published."""
    ConsentService(db).delete_draft(clause_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
