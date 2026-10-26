"""GDPR data-processing consent.

Two halves:

* Members accept the clause in force. Acceptance records *which version* they
  agreed to, not just that they agreed, so consent can be requested again when
  the terms of processing change — which GDPR requires.
* Superadmins author and publish new versions. Published versions are
  immutable: editing text somebody already accepted would destroy the evidence
  of what they agreed to, which is exactly what the accountability principle
  requires you to be able to produce.

The clause is platform-wide. There is a single level-1 entity, and every member
of every association is processed under the same terms.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consent_clause_model import ConsentClause
from app.models.user_model import User
from app.schemas.user import ConsentStatus

# Fallback used only when the table holds no published row — a database that
# has not been migrated, or one where the clause was unpublished by hand. The
# authoritative text lives in `consent_clauses`; migration a419bc6ef279 seeds
# this as version 1.0.
FALLBACK_VERSION = "1.0"

CONSENT_TEXT = """\
De acuerdo con el Reglamento (UE) 2016/679 (RGPD) y la Ley Orgánica 3/2018, te \
informamos de lo siguiente sobre el tratamiento de tus datos personales:

**Responsable.** La entidad a la que perteneces dentro de BoscoGest.

**Finalidad.** Gestionar tu condición de socio: altas y bajas, cuotas, \
inscripción en actividades, comunicaciones internas y publicaciones de la \
entidad.

**Legitimación.** La ejecución de la relación asociativa y tu consentimiento \
para los tratamientos que no sean necesarios para dicha relación.

**Datos tratados.** Datos identificativos y de contacto, DNI, fecha de \
nacimiento, dirección e IBAN cuando resulte necesario para la gestión de \
cuotas. Tu DNI e IBAN solo son visibles para quienes tengan atribuida esa \
función de gestión.

**Conservación.** Mientras mantengas la condición de socio y, después, durante \
los plazos legales de prescripción aplicables.

**Cesiones.** No se ceden datos a terceros salvo obligación legal o cuando sea \
imprescindible para prestar el servicio, como la entidad bancaria en el cobro \
de cuotas.

**Derechos.** Puedes ejercer los derechos de acceso, rectificación, supresión, \
oposición, limitación y portabilidad dirigiéndote a la entidad responsable, así \
como reclamar ante la Agencia Española de Protección de Datos.
"""


class ConsentService:
    def __init__(self, db: Session):
        self.db = db

    # ── Reading the clause in force ─────────────────────────────────────────

    def get_published_clause(self) -> Optional[ConsentClause]:
        return self.db.execute(
            select(ConsentClause).where(ConsentClause.is_published.is_(True))
        ).scalars().first()

    def _current_version_and_text(self) -> tuple[str, str]:
        clause = self.get_published_clause()
        if clause:
            return clause.version, clause.text
        return FALLBACK_VERSION, CONSENT_TEXT

    def get_status(self, user: User) -> ConsentStatus:
        version, text = self._current_version_and_text()
        # Consent given to a superseded version no longer counts: the user
        # agreed to different terms.
        accepted = (
            user.consent_accepted_at is not None and user.consent_version == version
        )
        return ConsentStatus(
            accepted=accepted,
            accepted_at=user.consent_accepted_at,
            accepted_version=user.consent_version,
            current_version=version,
            text=None if accepted else text,
        )

    def accept(self, user: User, version: str) -> ConsentStatus:
        current_version, _ = self._current_version_and_text()
        if version != current_version:
            # Stops a stale client from recording consent to a clause that has
            # since been replaced — consent that was never given to the text
            # now in force.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Consent version '{version}' is out of date; "
                    f"the current version is '{current_version}'. "
                    "Reload and review the clause again."
                ),
            )

        db_user = self.db.execute(
            select(User).where(User.id == user.id)
        ).scalars().first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        db_user.consent_accepted_at = datetime.now(timezone.utc)
        db_user.consent_version = current_version
        self.db.commit()
        self.db.refresh(db_user)
        return self.get_status(db_user)

    # ── Authoring versions ──────────────────────────────────────────────────

    def list_clauses(self) -> List[ConsentClause]:
        return list(
            self.db.execute(
                # id breaks the tie: two versions created within the same
                # timestamp resolution would otherwise list unpredictably.
                select(ConsentClause).order_by(
                    ConsentClause.created_at.desc(), ConsentClause.id.desc()
                )
            ).scalars().all()
        )

    def get_clause(self, clause_id: int) -> ConsentClause:
        clause = self.db.get(ConsentClause, clause_id)
        if not clause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found"
            )
        return clause

    def create_clause(
        self, version: str, text: str, author: User, publish: bool = False
    ) -> ConsentClause:
        version = version.strip()
        text = text.strip()
        if not version:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Version is required",
            )
        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Clause text is required",
            )

        existing = self.db.execute(
            select(ConsentClause).where(ConsentClause.version == version)
        ).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Version '{version}' already exists",
            )

        clause = ConsentClause(
            version=version,
            text=text,
            is_published=False,
            created_by_id=author.id,
        )
        self.db.add(clause)
        self.db.flush()

        if publish:
            self._publish(clause)
        self.db.commit()
        self.db.refresh(clause)
        return clause

    def update_draft(self, clause_id: int, text: str) -> ConsentClause:
        clause = self.get_clause(clause_id)
        if clause.is_published:
            # The whole point of versioning: a published clause is the record
            # of what people accepted, so it cannot be rewritten under them.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Published clauses are immutable — members have already "
                    "accepted this text. Create a new version instead."
                ),
            )
        text = text.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Clause text is required",
            )
        clause.text = text
        self.db.commit()
        self.db.refresh(clause)
        return clause

    def publish_clause(self, clause_id: int) -> ConsentClause:
        clause = self.get_clause(clause_id)
        if clause.is_published:
            return clause
        self._publish(clause)
        self.db.commit()
        self.db.refresh(clause)
        return clause

    def _publish(self, clause: ConsentClause) -> None:
        """Make `clause` the one in force.

        A partial unique index enforces a single published row, so the previous
        one has to be stood down in the same transaction. Publishing makes every
        member reaccept on their next login.
        """
        for other in self.db.execute(
            select(ConsentClause).where(ConsentClause.is_published.is_(True))
        ).scalars().all():
            other.is_published = False
        self.db.flush()

        clause.is_published = True
        clause.published_at = datetime.now(timezone.utc)
        self.db.flush()

    def delete_draft(self, clause_id: int) -> None:
        clause = self.get_clause(clause_id)
        if clause.is_published:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the clause currently in force",
            )
        if clause.published_at is not None:
            # It was in force at some point, so somebody may have accepted it;
            # the record has to survive.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This version was published in the past and may have been "
                    "accepted; it cannot be deleted."
                ),
            )
        self.db.delete(clause)
        self.db.commit()

    def pending_acceptance_count(self, version: str) -> int:
        """How many active users have yet to accept the given version."""
        from sqlalchemy import func, or_

        return self.db.execute(
            select(func.count(User.id)).where(
                User.is_active.is_(True),
                or_(
                    User.consent_version.is_(None),
                    User.consent_version != version,
                ),
            )
        ).scalar_one()


def get_consent_service(db: Session) -> ConsentService:
    return ConsentService(db)
