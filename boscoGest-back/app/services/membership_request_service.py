from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.membership_model import Membership
from app.models.membership_request_model import MembershipRequest
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.models.user_model import User
from app.repositories.membership_request_repository import MembershipRequestRepository
from app.repositories.membership_repository import MembershipRepository
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, EventType
from app.services.membership_service import MembershipService
from app.utils.auth import get_sync_db


class MembershipRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.request_repo = MembershipRequestRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.membership_service = MembershipService(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    # ── Public: create request (called after user self-registers) ──────────

    def create_request(
        self,
        user_id: int,
        entity_id: int,
        message: Optional[str] = None,
    ) -> MembershipRequest:
        entity = self.db.get(Entity, entity_id)
        if not entity or not entity.is_active:
            raise HTTPException(status_code=404, detail="Entity not found")

        existing_membership = self.membership_repo.get_by_user_and_entity(
            user_id, entity_id, active_only=True
        )
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya es miembro de esta entidad",
            )

        existing_request = self.request_repo.get_pending_by_user_and_entity(
            user_id, entity_id
        )
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una solicitud pendiente para esta entidad",
            )

        req = MembershipRequest(
            user_id=user_id,
            entity_id=entity_id,
            message=message,
            status="pending",
        )
        req = self.request_repo.create(req)
        self.db.commit()
        self.db.refresh(req)

        # Notify entity admins
        user = self.db.get(User, user_id)
        admin_ids = self._get_entity_reviewer_ids(entity_id)
        if admin_ids and user:
            self.notification_service.notify(
                event_type=EventType.MEMBERSHIP_REQUEST_CREATED,
                entity_id=entity_id,
                actor=user,
                resource_type="membership_requests",
                resource_id=req.id,
                title=f"Nueva solicitud de membresía en {entity.name}",
                body=f"{user.name} {user.surname} quiere unirse a {entity.name}",
                recipient_ids=admin_ids,
            )

        return req

    # ── Admin: list requests ────────────────────────────────────────────────

    def list_requests_for_admin(
        self,
        current_user: User,
        entity_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[MembershipRequest]:
        if entity_id:
            self.auth_service.check_entity_permission(
                current_user, entity_id, "memberships", "review"
            )
            return self.request_repo.list_by_entity(entity_id, status=status_filter)

        manageable_ids = self._get_manageable_entity_ids(current_user)
        result = []
        for eid in manageable_ids:
            result.extend(self.request_repo.list_by_entity(eid, status=status_filter))
        return result

    # ── User: list own requests ─────────────────────────────────────────────

    def list_my_requests(self, user_id: int) -> List[MembershipRequest]:
        return self.request_repo.list_by_user(user_id)

    # ── Admin: accept ───────────────────────────────────────────────────────

    def accept_request(
        self,
        request_id: int,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> MembershipRequest:
        req = self.request_repo.get_by_id(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La solicitud ya está {req.status}",
            )

        self.auth_service.check_entity_permission(
            current_user, req.entity_id, "memberships", "review"
        )

        socio_role = self.db.execute(
            select(Role).where(Role.name == "socio", Role.is_active == True)
        ).scalars().first()
        if not socio_role:
            raise HTTPException(
                status_code=500, detail="El rol 'socio' no existe en el sistema"
            )

        # Create membership directly (no permission check — reviewer authorizes this)
        existing = self.membership_repo.get_by_user_and_entity(
            req.user_id, req.entity_id, active_only=True
        )
        if not existing:
            db_membership = Membership(
                user_id=req.user_id,
                role_id=socio_role.id,
                entity_id=req.entity_id,
                is_active=True,
            )
            self.db.add(db_membership)
            self.db.flush()

            entity = self.db.get(Entity, req.entity_id)
            self.notification_service.notify(
                event_type=EventType.MEMBERSHIP_CREATED,
                entity_id=req.entity_id,
                actor=current_user,
                resource_type="memberships",
                resource_id=db_membership.id,
                title=f"Bienvenido a {entity.name}",
                body=f"Tu membresía en {entity.name} ha sido activada",
                recipient_ids=[req.user_id],
            )

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="memberships",
                resource_id=db_membership.id,
                details={
                    "user_id": req.user_id,
                    "entity_id": req.entity_id,
                    "role_id": socio_role.id,
                    "via_membership_request": request_id,
                },
                ip_address=ip_address,
            )

            # Create memberships in parent entities with socio role
            self.membership_service.create_parent_memberships(
                req.user_id, req.entity_id, current_user, ip_address=ip_address
            )

        # Mark request as accepted
        req = self.request_repo.update_status(
            request_id, status="accepted", reviewed_by_id=current_user.id
        )
        self.db.commit()
        self.db.refresh(req)

        entity = self.db.get(Entity, req.entity_id)
        self.notification_service.notify(
            event_type=EventType.MEMBERSHIP_REQUEST_ACCEPTED,
            entity_id=req.entity_id,
            actor=current_user,
            resource_type="membership_requests",
            resource_id=req.id,
            title=f"Solicitud aceptada en {entity.name}",
            body=f"Tu solicitud para unirte a {entity.name} ha sido aceptada",
            recipient_ids=[req.user_id],
        )

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="accept",
            resource_type="membership_requests",
            resource_id=request_id,
            details={"target_user_id": req.user_id, "entity_id": req.entity_id},
            ip_address=ip_address,
        )

        return req

    # ── Admin: reject ───────────────────────────────────────────────────────

    def reject_request(
        self,
        request_id: int,
        current_user: User,
        rejection_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> MembershipRequest:
        req = self.request_repo.get_by_id(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La solicitud ya está {req.status}",
            )

        self.auth_service.check_entity_permission(
            current_user, req.entity_id, "memberships", "review"
        )

        req = self.request_repo.update_status(
            request_id,
            status="rejected",
            reviewed_by_id=current_user.id,
            rejection_reason=rejection_reason,
        )
        self.db.commit()
        self.db.refresh(req)

        entity = self.db.get(Entity, req.entity_id)
        body = f"Tu solicitud para unirte a {entity.name} ha sido rechazada"
        if rejection_reason:
            body += f": {rejection_reason}"

        self.notification_service.notify(
            event_type=EventType.MEMBERSHIP_REQUEST_REJECTED,
            entity_id=req.entity_id,
            actor=current_user,
            resource_type="membership_requests",
            resource_id=req.id,
            title=f"Solicitud rechazada en {entity.name}",
            body=body,
            recipient_ids=[req.user_id],
        )

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="reject",
            resource_type="membership_requests",
            resource_id=request_id,
            details={
                "target_user_id": req.user_id,
                "entity_id": req.entity_id,
                "rejection_reason": rejection_reason,
            },
            ip_address=ip_address,
        )

        return req

    # ── User: cancel own pending request ───────────────────────────────────

    def cancel_request(
        self, request_id: int, current_user: User
    ) -> None:
        req = self.request_repo.get_by_id(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="No es tu solicitud")
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden cancelar solicitudes pendientes",
            )

        self.request_repo.hard_delete(request_id)
        self.db.commit()

    # ── Private helpers ─────────────────────────────────────────────────────

    def _get_entity_reviewer_ids(self, entity_id: int) -> List[int]:
        """Return user IDs of members who can review membership requests for this entity."""
        stmt = select(Membership.user_id).where(
            Membership.entity_id == entity_id,
            Membership.is_active == True,
        )
        member_ids = list(self.db.execute(stmt).scalars().all())

        reviewers = []
        for uid in member_ids:
            user = self.db.get(User, uid)
            if user and self.auth_service.has_effective_permission(
                user, entity_id, "memberships", "review"
            ):
                reviewers.append(uid)
        return reviewers

    def _get_manageable_entity_ids(self, current_user: User) -> List[int]:
        """Return entity IDs where current_user can review membership requests."""
        stmt = select(Membership.entity_id).where(
            Membership.user_id == current_user.id,
            Membership.is_active == True,
        )
        entity_ids = list(self.db.execute(stmt).scalars().all())
        return [
            eid for eid in entity_ids
            if self.auth_service.has_effective_permission(
                current_user, eid, "memberships", "review"
            )
        ]


def get_membership_request_service(
    db: Session = Depends(get_sync_db),
) -> MembershipRequestService:
    return MembershipRequestService(db)
