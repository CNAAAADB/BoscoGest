from typing import List, Dict, Any, Optional
import re
import secrets
from datetime import date, datetime, timezone
import logging
import time
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, func, select, update
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.models.notification_model import DeviceToken
from app.models.permission_model import Permission
from app.models.relationships import entity_roles, role_permissions
from app.models.bulk_upload_job_model import BulkUploadJob
from app.services.csv_validation import EMAIL_RE, parse_birthdate
from app.services.member_file import UnreadableFile, read_member_file
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PasswordChange,
    FirstTimePasswordChange,
    PaginatedUsers,
    ALLOWED_SIZES,
)
from app.services.user_visibility import UserVisibility
from app.services.member_review import requires_review
from app.repositories.user_repository import UserRepository
from app.repositories.membership_repository import MembershipRepository
from app.services.membership_service import MembershipService
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db, get_password_hash, verify_password
from app.services.storage import get_storage_service
import uuid
from urllib.parse import urlparse

logger = logging.getLogger(__name__)



def generate_unusable_password() -> str:
    """A password nobody is meant to know.

    Every account needs a hash in the column, but the people these are minted
    for never type a password: they arrive through the one-shot link in their
    welcome email and choose their own there. Generating one here is what lets
    the CSV drop its ``password`` column, so a file full of members no longer
    travels with clear-text credentials in it.

    Long and random on purpose — this value is never shown, never stored in the
    clear, and never has to be typed, so there is no reason to make it guessable
    or memorable.
    """
    return secrets.token_urlsafe(32)




def _safe_row_error(exc: Exception) -> str:
    """A description of a failed row that carries no personal data.

    ValueError is ours — the row-level checks raise it with wording written to
    be shown. Anything else comes from below and may quote the data, so it is
    reduced to what kind of failure it was.
    """
    if isinstance(exc, ValueError):
        return str(exc)

    detail = str(getattr(exc, "orig", exc)).lower()
    if "value too long" in detail:
        return (
            "Un campo supera la longitud permitida. Revisa sobre todo el IBAN "
            "y la dirección."
        )
    if "not-null" in detail or "null value" in detail:
        return "Falta un campo obligatorio."
    if "invalid input syntax" in detail or "invalid input value" in detail:
        return "Un campo tiene un formato que la base de datos no acepta."
    return "No se ha podido crear este usuario. El detalle está en el registro del servidor."


def _describe_unique_clash(exc: Exception) -> str:
    """Which field was already taken.

    Three columns are unique — email, phone and DNI — but the message only ever
    named two of them, so a repeated phone number was reported as a duplicate
    email or DNI and sent whoever hit it looking in the wrong place.
    """
    detail = str(getattr(exc, "orig", exc)).lower()
    for column, label in (
        ("email", "Ya existe un usuario con ese email"),
        ("phone", "Ya existe un usuario con ese teléfono"),
        ("dni", "Ya existe un usuario con ese DNI"),
    ):
        if column in detail:
            return label
    return "Ya existe un usuario con ese email, teléfono o DNI"


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.membership_service = MembershipService(db)
        self.auth_service = AuthorizationService(db)
        self.audit_service = AuditService(db)

    def create_user(
        self,
        user_in: UserCreate,
        current_user: User,
        ip_address: str | None = None,
    ) -> User:
        try:
            membership_entity_id = user_in.entity_id
            membership_role_id = user_in.role_id
            use_default_membership = False

            if user_in.entity_id is None or user_in.role_id is None:
                use_default_membership = True
                first_membership = self.db.execute(
                    select(Membership)
                    .where(
                        Membership.user_id == current_user.id,
                        Membership.is_active == True,
                    )
                    .order_by(Membership.created_at.asc())
                ).scalars().first()

                if not first_membership:
                    raise HTTPException(
                        status_code=403,
                        detail="User has no active memberships",
                    )
                membership_entity_id = first_membership.entity_id

                socio_role = self.db.execute(
                    select(Role).where(
                        Role.name == "socio", Role.is_active == True
                    )
                ).scalars().first()
                if not socio_role:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Default 'socio' role not found in the system",
                    )
                membership_role_id = socio_role.id
            else:
                entity = self.db.execute(
                    select(Entity).where(
                        Entity.id == user_in.entity_id,
                        Entity.is_active == True,
                    )
                ).scalars().first()
                if not entity:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Entity with id {user_in.entity_id} not found or inactive",
                    )

                role = self.db.execute(
                    select(Role).where(
                        Role.id == user_in.role_id, Role.is_active == True
                    )
                ).scalars().first()
                if not role:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Role with id {user_in.role_id} not found or inactive",
                    )

            self.auth_service.check_entity_permission(
                current_user, membership_entity_id, "users", "create"
            )

            self.auth_service.check_superadmin_assignment(
                current_user, self.db.get(Entity, membership_entity_id),
                self.db.get(Role, membership_role_id)
            )

            # Generated, not supplied: nobody is told it and nobody types it.
            # They arrive through the link in their welcome email.
            hashed_password = get_password_hash(generate_unusable_password())

            db_user = User(
                email=user_in.email,
                password_hash=hashed_password,
                name=user_in.name,
                surname=user_in.surname,
                phone=user_in.phone,
                address=user_in.address,
                birthdate=user_in.birthdate,
                dni=user_in.dni,
                photo=user_in.photo,
                iban=user_in.iban,
                size=user_in.size,
                hobbies=user_in.hobbies,
                job_position=user_in.job_position,
                is_active=True,
                must_change_password=True,
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)

            membership = Membership(
                user_id=db_user.id,
                entity_id=membership_entity_id,
                role_id=membership_role_id,
                is_active=True,
            )
            self.db.add(membership)
            self.db.commit()
            self.db.refresh(membership)

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="memberships",
                resource_id=membership.id,
                details={
                    "user_id": db_user.id,
                    "entity_id": membership_entity_id,
                    "role_id": membership_role_id,
                    "created_with_user": True,
                    "is_default": use_default_membership,
                },
                ip_address=ip_address,
            )

            # Create parent entity memberships (consolidated logic)
            self.membership_service.create_parent_memberships(
                db_user.id,
                membership_entity_id,
                current_user,
                ip_address=ip_address,
            )

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="create",
                resource_type="users",
                resource_id=db_user.id,
                details={
                    "email": user_in.email,
                    "dni": user_in.dni,
                    "name": f"{user_in.name} {user_in.surname}",
                    "membership_created": True,
                    "default_membership": use_default_membership,
                },
                ip_address=ip_address,
            )

            return db_user

        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_describe_unique_clash(exc),
            )

    def get_member_directory(
        self, skip: int = 0, limit: int = 25,
        search: str | None = None, entity_id: int | None = None,
    ) -> dict:
        """Cross-association directory: minimum information to start an in-app chat.

        Only active users with a current local-association membership are
        listed. No email, phone, DNI or other private field is returned.
        All filter/count operations occur in SQL, before pagination.
        """
        from sqlalchemy import or_
        from app.models.entity_model import Entity

        if entity_id is not None:
            association = self.db.get(Entity, entity_id)
            if association is None or not association.is_active or association.level != 4:
                raise HTTPException(status_code=400, detail="Selecciona una asociación local válida")

        query = (
            select(User.id, User.name, User.surname)
            .join(Membership, Membership.user_id == User.id)
            .join(Entity, Entity.id == Membership.entity_id)
            .where(
                User.is_active == True,
                Membership.is_active == True,
                Entity.is_active == True,
                Entity.level == 4,
            )
        )
        if entity_id is not None:
            query = query.where(Entity.id == entity_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
                match = lambda field: func.unaccent(field).ilike(func.unaccent(term))
            else:
                match = lambda field: field.ilike(term)
            query = query.where(or_(
                match(User.name), match(User.surname),
                match(User.name + " " + User.surname)
            ))
        result = query.distinct()
        count = self.db.execute(
            select(func.count()).select_from(result.subquery())
        ).scalar_one()
        rows = self.db.execute(
            result.order_by(User.surname, User.name, User.id)
            .offset(skip).limit(limit)
        ).all()
        return {
            "items": [{"id": row.id, "name": row.name, "surname": row.surname} for row in rows],
            "total": count, "skip": skip, "limit": limit,
        }

    def get_manageable_local_associations(self, current_user: User) -> list[dict]:
        """Filter the selector by actual management permission, not membership."""
        accessible = self.auth_service.get_accessible_entity_ids(current_user)
        if not accessible:
            return []
        entities = self.db.execute(
            select(Entity)
            .where(Entity.id.in_(accessible), Entity.is_active == True, Entity.level == 4)
            .order_by(Entity.name)
        ).scalars().all()
        return [
            {"id": entity.id, "name": entity.name}
            for entity in entities
            if self.auth_service.has_effective_permission(
                current_user, entity.id, "users", "manage"
            )
        ]

    def list_users_in_scope(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        review_only: bool = False,
        entity_id: int | None = None,
        managed_only: bool = False,
    ) -> PaginatedUsers:
        """A page of the users the caller can reach, redacted to their tier.

        get_managed_users and get_users had identical bodies; this is the single
        implementation both now delegate to.
        """
        # Diagnostic timings contain only aggregate durations and row counts:
        # never log search strings or member-identifying data.
        started = time.perf_counter()
        accessible_entity_ids = self.auth_service.get_accessible_entity_ids(
            current_user
        )
        if managed_only:
            # Scope ADMIN users to associations where management is actually
            # granted; merely belonging to an association is not sufficient.
            accessible_entity_ids = [
                eid for eid in accessible_entity_ids
                if self.auth_service.has_effective_permission(
                    current_user, eid, "users", "manage"
                )
            ]
        # A selected association must both be reachable and be a local
        # association (level 4); parent/federation IDs cannot broaden scope.
        if entity_id is not None:
            selected = self.db.get(Entity, entity_id)
            if (entity_id not in accessible_entity_ids or selected is None
                    or not selected.is_active or selected.level != 4):
                raise HTTPException(status_code=403, detail="Asociación no accesible")
        scope_end = time.perf_counter()
        if not accessible_entity_ids:
            return PaginatedUsers(items=[], total=0, skip=skip, limit=limit)

        visibility = UserVisibility.for_viewer(self.auth_service, current_user)
        if review_only:
            # Filtering *after* paging hides later matches and gives a wrong
            # total. Scan the scoped result set in bounded batches and paginate
            # the matches, so every page and the total are correct. This path
            # is opt-in; ordinary user listings retain their fast SQL paging.
            if not self.auth_service.has_global_permission(current_user, "users", "update"):
                raise HTTPException(status_code=403, detail="Permission denied")
            users = []
            total = 0
            offset = 0
            batch_size = 200
            while True:
                batch = self.user_repo.get_by_entity_ids(
                    accessible_entity_ids, skip=offset, limit=batch_size, search=search, entity_id=entity_id
                )
                for candidate in batch:
                    can_contact = visibility.can_read_contact or candidate.id == current_user.id
                    can_sensitive = visibility.can_read_sensitive or candidate.id == current_user.id
                    if requires_review(candidate, contact=can_contact, sensitive=can_sensitive):
                        if skip <= total < skip + limit:
                            users.append(candidate)
                        total += 1
                offset += len(batch)
                if len(batch) < batch_size:
                    break
            list_end = time.perf_counter()
            count_end = list_end
        else:
            users = self.user_repo.get_by_entity_ids(
                accessible_entity_ids, skip=skip, limit=limit, search=search, entity_id=entity_id
            )
            list_end = time.perf_counter()
            total = self.user_repo.count_by_entity_ids(
                accessible_entity_ids, search=search, entity_id=entity_id
            )
            count_end = time.perf_counter()

        # Resolved once for the whole page rather than per row: it walks
        # memberships, groups and direct permissions.
        response = PaginatedUsers(
            items=[visibility.serialize(u, viewer_id=current_user.id) for u in users],
            total=total,
            skip=skip,
            limit=limit,
        )
        finished = time.perf_counter()
        elapsed_ms = (finished - started) * 1000
        if elapsed_ms >= 500:
            logger.warning(
                "Slow user listing: total_ms=%.1f scope_ms=%.1f "
                "list_ms=%.1f count_ms=%.1f serialize_ms=%.1f "
                "page_size=%d returned=%d matching_total=%d scope_entities=%d "
                "has_search=%s",
                elapsed_ms,
                (scope_end - started) * 1000,
                (list_end - scope_end) * 1000,
                (count_end - list_end) * 1000,
                (finished - count_end) * 1000,
                limit,
                len(users),
                total,
                len(accessible_entity_ids),
                bool(search),
            )
        return response

    def get_managed_users(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        review_only: bool = False,
        entity_id: int | None = None,
    ) -> PaginatedUsers:
        return self.list_users_in_scope(
            current_user, skip, limit, search, review_only=review_only,
            entity_id=entity_id, managed_only=True
        )

    def get_users(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        entity_id: int | None = None,
    ) -> PaginatedUsers:
        return self.list_users_in_scope(current_user, skip, limit, search, entity_id=entity_id)

    def search_by_email(self, email: str) -> User:
        db_user = self.user_repo.get_by_email(email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found",
            )
        return db_user

    def search_by_dni(self, dni: str) -> User:
        db_user = self.user_repo.get_by_dni(dni)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with DNI '{dni}' not found",
            )
        return db_user

    def get_user(self, user_id: int) -> User:
        db_user = self.user_repo.get_by_id_with_details(user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user

    def ensure_reachable(
        self, current_user: User, db_user: User, action: str, detail: str = "User not found"
    ) -> User:
        """404 unless `db_user` is within `current_user`'s reach for `action`.

        The routes by id only required the permission somewhere, so any member
        could read the name, email and phone of anyone by trying ids. Not
        found rather than forbidden, so that trying ids does not reveal which
        ones exist either.
        """
        if not self.auth_service.can_reach_user(current_user, db_user, action):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return db_user

    def set_user_photo(
        self,
        user_id: int,
        data: bytes,
        content_type: str | None,
        current_user: User,
        ip_address: str | None = None,
    ) -> User:
        """Upload a profile photo to storage and save its URL on the user.
        Mirrors ChatService.upload_group_avatar."""
        db_user = self.user_repo.get_by_id(user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        self.ensure_reachable(current_user, db_user, "update")

        if not content_type or not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo debe ser una imagen",
            )
        max_size = 5 * 1024 * 1024  # 5 MB
        if len(data) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La imagen no puede superar los 5 MB",
            )

        ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
        key = f"users/avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
        storage = get_storage_service()
        storage.upload(key, data, content_type)
        url = storage.get_presigned_url(key, expires_in=86400 * 365)

        self.user_repo.update(user_id, {"photo": url})
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="update",
            resource_type="users",
            resource_id=user_id,
            details={"photo_updated": True},
            ip_address=ip_address,
        )
        return self.user_repo.get_by_id(
            user_id, options=UserRepository._base_eager_options()
        )

    def update_own_profile(
        self,
        current_user: User,
        user_update: UserUpdate,
        ip_address: str | None = None,
    ) -> User:
        """Self-service profile update. Users cannot change their own active
        status; that field is stripped before delegating to update_user."""
        data = user_update.model_dump(exclude_unset=True)
        data.pop("is_active", None)
        # Unlike an administrative member record, an active self-service
        # account needs a login identifier. Prevent accidental lockout.
        email = data.get("email", current_user.email)
        phone = data.get("phone", current_user.phone)
        if not (email or phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Para mantener el acceso a tu cuenta, conserva al menos "
                    "un correo electrónico o un teléfono."
                ),
            )
        clean = UserUpdate(**data)
        return self.update_user(
            current_user.id, clean, current_user, ip_address=ip_address
        )

    def update_user(
        self,
        user_id: int,
        user_update: UserUpdate,
        current_user: User,
        ip_address: str | None = None,
    ) -> User:
        db_user = self.user_repo.get_by_id(user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        self.ensure_reachable(current_user, db_user, "update")

        update_data = user_update.model_dump(exclude_unset=True)
        # JSON-safe copy for the audit log (datetime.date is not JSON-serialisable)
        audit_data = user_update.model_dump(exclude_unset=True, mode="json")

        # La ficha de un socio puede existir sin medios de contacto.
        # Su contraseña inicial es aleatoria y desconocida: sin un
        # identificador no se puede iniciar sesión ni recuperar el acceso.
        try:
            if update_data:
                self.user_repo.update(user_id, update_data)
                self.db.commit()

            db_user = self.user_repo.get_by_id(
                user_id, options=UserRepository._base_eager_options()
            )

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="update",
                resource_type="users",
                resource_id=user_id,
                details=audit_data,
                ip_address=ip_address,
            )

            return db_user

        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_describe_unique_clash(exc),
            )

    def delete_user(
        self,
        user_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> None:
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own user account",
            )

        db_user = self.user_repo.get_by_id(user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        self.ensure_reachable(current_user, db_user, "delete")

        email = db_user.email
        self.user_repo.soft_delete(user_id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="delete",
            resource_type="users",
            resource_id=user_id,
            details={"email": email},
            ip_address=ip_address,
        )

    def delete_own_account(
        self,
        current_user: User,
        password: str,
        ip_address: str | None = None,
    ) -> None:
        """Erase the caller's own account, at their own request.

        Anyone who can sign themselves up has to be able to undo that from
        inside the app — it is what Google Play asks of an app with a public
        registration form, and what the GDPR asks of us regardless.

        The row survives and is stripped instead of being dropped. Memberships,
        fees and audit entries point at it, and an association's books still
        have to add up after somebody leaves; what goes is everything that
        identifies the person behind it.
        """
        db_user = self.user_repo.get_by_id(current_user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="La contraseña no es correcta",
            )

        if self._is_last_superadmin(db_user):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Eres la única cuenta con administración total. Traspasa ese "
                    "rol a otra persona antes de eliminar la tuya."
                ),
            )

        self._purge_avatar(db_user.photo)

        self.db.execute(
            update(Membership)
            .where(Membership.user_id == db_user.id)
            .values(is_active=False)
        )
        # Los dispositivos registrados para recibir notificaciones push. Sin
        # esto, un móvil que ya no pertenece a nadie de la asociación seguiría
        # siendo un destinatario válido, y el token es en sí un identificador
        # del aparato: forma parte de lo que hay que borrar.
        self.db.execute(
            delete(DeviceToken).where(DeviceToken.user_id == db_user.id)
        )
        db_user.direct_permissions.clear()
        db_user.groups.clear()

        db_user.name = "Cuenta"
        db_user.surname = "eliminada"
        db_user.email = None
        db_user.phone = None
        db_user.address = None
        db_user.photo = None
        db_user.iban = None
        db_user.size = None
        db_user.hobbies = None
        db_user.job_position = None
        # DNI is nullable: deletion can remove it completely.
        db_user.dni = None
        db_user.birthdate = date(1900, 1, 1)
        # A hash of a secret nobody holds: the account can no longer be signed
        # into, and the old hash is gone with it.
        db_user.password_hash = get_password_hash(generate_unusable_password())
        db_user.consent_accepted_at = None
        db_user.consent_version = None
        db_user.must_change_password = False
        db_user.is_active = False

        self.db.commit()

        # Deliberately no email or name in the details: the point of the
        # operation is that those stop existing here.
        self.audit_service.create_audit_log(
            user_id=db_user.id,
            action="delete",
            resource_type="users",
            resource_id=db_user.id,
            details={"self_service": True},
            ip_address=ip_address,
        )

    def _is_last_superadmin(self, db_user: User) -> bool:
        """Whether this is the only active account that can administer anything.

        Letting it delete itself would leave the installation with nobody able
        to hand the role to anyone else, and no way back in.
        """
        has_manage_all = any(
            m.is_active and any(p.action == "manage_all" for p in m.role.permissions)
            for m in db_user.memberships
        )
        if not has_manage_all:
            return False

        others = self.db.execute(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(Membership, Membership.user_id == User.id)
            .join(role_permissions, role_permissions.c.role_id == Membership.role_id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                User.id != db_user.id,
                User.is_active == True,
                Membership.is_active == True,
                Permission.action == "manage_all",
            )
        ).scalar_one()
        return others == 0

    def _purge_avatar(self, photo_url: str | None) -> None:
        """Best-effort removal of the avatar object behind a stored URL.

        The column holds a presigned URL rather than the key it was built from,
        so the key is read back out of the path. Storage failing must not stop
        an account deletion — the reference is about to disappear either way.
        """
        if not photo_url:
            return
        marker = "users/avatars/"
        try:
            path = urlparse(photo_url).path.lstrip("/")
            if marker not in path:
                return
            get_storage_service().delete(path[path.index(marker):])
        except Exception:
            logger.warning(
                "Could not delete the avatar of a deleted account", exc_info=True
            )

    def get_user_creatable_entities(self, current_user: User) -> List[Dict[str, Any]]:
        """Return the entities where the user can create users, for selectors."""
        accessible_ids = self.auth_service.get_accessible_entity_ids(current_user)
        creatable_ids = [
            eid for eid in accessible_ids
            if self.auth_service.has_effective_permission(
                current_user, eid, "users", "create"
            )
        ]
        if not creatable_ids:
            return []
        entities = self.db.execute(
            select(Entity)
            .where(Entity.id.in_(creatable_ids), Entity.is_active == True)
            .order_by(Entity.name)
        ).scalars().all()
        return [{"id": e.id, "name": e.name} for e in entities]

    def get_assignable_roles(
        self, entity_id: int, current_user: User
    ) -> List[Dict[str, Any]]:
        """Roles that belong to the given association and that the current user
        may assign when creating users there. Used to populate the role selector
        of the bulk import (conditioned on the selected association)."""
        entity = self.db.execute(
            select(Entity).where(Entity.id == entity_id, Entity.is_active == True)
        ).scalars().first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asociación no encontrada o inactiva",
            )

        # Same gate as the bulk upload itself: the user must be able to create
        # users in this association.
        self.auth_service.check_entity_permission(
            current_user, entity_id, "users", "create"
        )

        roles = list(
            self.db.execute(
                select(Role)
                .join(entity_roles, entity_roles.c.role_id == Role.id)
                .where(
                    entity_roles.c.entity_id == entity_id,
                    Role.is_active == True,
                )
                .order_by(Role.name)
            ).scalars().all()
        )

        from app.utils.auth import is_root_superadmin
        if entity.level != 1 or not is_root_superadmin(current_user):
            roles = [r for r in roles if r.name != "superadmin"]

        return [
            {"id": r.id, "name": r.name, "description": r.description}
            for r in roles
        ]

    def create_bulk_upload_job(
        self,
        file_content: bytes,
        filename: str,
        current_user: User,
        entity_id: int,
        role_id: int,
    ) -> BulkUploadJob:
        """Validate the file headers and create a pending job record.

        The file can be a CSV or an Excel workbook (.xlsx); both are read by
        ``read_member_file``, which is also what the job uses later.

        The association (entity_id) and the role (role_id) are chosen in the UI
        and applied to every row, so they are no longer expected as CSV
        columns."""
        # The user must be allowed to create users in the selected entity, and
        # the selected role must be one they may assign in that association.
        assignable_role_ids = {
            r["id"] for r in self.get_assignable_roles(entity_id, current_user)
        }
        if role_id not in assignable_role_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol seleccionado no es válido para esta asociación",
            )

        try:
            file_columns, _ = read_member_file(file_content, filename)
        except UnreadableFile as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # DNI, email y teléfono son opcionales para las fichas de socios.
        # entity_id y role_id ya no se leen del CSV: vienen de los selectores
        # de asociación y rol.
        # password tampoco: se genera una por fila y nadie llega a conocerla,
        # porque el acceso inicial va por el enlace del correo de bienvenida.
        # Así el fichero deja de contener contraseñas en claro.
        required_columns = [
            "name", "surname",
            "birthdate",
        ]
        csv_columns = file_columns
        missing_columns = [
            col for col in required_columns if col not in csv_columns
        ]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}",
            )

        job = BulkUploadJob(
            created_by_id=current_user.id,
            target_entity_id=entity_id,
            target_role_id=role_id,
            status="pending",
            csv_filename=filename,
            csv_content=file_content,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_bulk_upload_job(self, job_id: int, current_user: User) -> BulkUploadJob:
        job = self.db.execute(
            select(BulkUploadJob).where(BulkUploadJob.id == job_id)
        ).scalars().first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job

    def list_bulk_upload_jobs(self, current_user: User) -> List[BulkUploadJob]:
        return list(
            self.db.execute(
                select(BulkUploadJob).order_by(BulkUploadJob.created_at.desc())
            ).scalars().all()
        )

    def issue_activation_link(
        self,
        user_id: int,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        """Mint a fresh sign-in link for someone and hand it to the caller.

        For the people the welcome email cannot reach: those registered with a
        phone and no address, and those whose message never arrived. The
        administrator passes the link on by whatever means they already use.

        Restricted to accounts that have never set a password of their own.
        That is deliberate: for those, whoever administers them could already
        get in — until now they were the one who typed the initial password —
        so this grants nothing new. Extending it to someone who has since
        chosen their own password would turn an administrator into someone who
        can enter any account they manage, which is a different thing entirely.
        """
        from app.services import activation_service

        db_user = self.user_repo.get_by_id(user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        # The check hangs off where they belong. Someone with no association
        # has nobody who administers them, so there is no one to authorise this.
        entity_ids = self.membership_repo.get_entity_ids_by_user(user_id)
        if not entity_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Este usuario no pertenece a ninguna asociación, así que no "
                    "hay dónde comprobar quién puede darle acceso."
                ),
            )

        # Being able to create users in any one of their associations is
        # enough: that is the same gate that let someone set this account's
        # initial password in the first place.
        for entity_id in entity_ids:
            try:
                self.auth_service.check_entity_permission(
                    current_user, entity_id, "users", "create"
                )
                break
            except HTTPException:
                continue
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para dar acceso a este usuario.",
            )

        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este usuario está dado de baja.",
            )

        if not db_user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Este usuario ya eligió su contraseña, así que debe entrar "
                    "con ella. Si la ha olvidado, tendrá que restablecerla él "
                    "mismo."
                ),
            )

        # An activation link is not useful if the member has no way to log in
        # after choosing their password. Add a unique email or phone first.
        if not (db_user.email or db_user.phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Antes de activar esta cuenta, añade un correo o teléfono "
                    "al socio para que pueda iniciar sesión después."
                ),
            )

        raw_token = activation_service.issue_token(self.db, db_user)

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="issue_activation_link",
            resource_type="users",
            resource_id=db_user.id,
            details={"email": db_user.email},
            ip_address=ip_address,
        )

        return {
            "url": activation_service.build_activation_url(raw_token),
            "expires_in_hours": activation_service.TOKEN_TTL_HOURS,
        }

    def change_password(
        self,
        password_data: PasswordChange,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        if not verify_password(
            password_data.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        if verify_password(
            password_data.new_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        new_hashed_password = get_password_hash(password_data.new_password)
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(password_hash=new_hashed_password)
        )
        self.db.execute(stmt)
        # A reset link asked for and then not needed after all must not stay
        # usable once the password has changed.
        from app.services import activation_service

        activation_service.invalidate_tokens_for_user(
            self.db, current_user.id, commit=False
        )
        from app.services.refresh_session_service import revoke_user_sessions
        revoke_user_sessions(self.db, current_user.id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="change_password",
            resource_type="users",
            resource_id=current_user.id,
            details={
                "email": current_user.email,
                "changed_by_self": True,
            },
            ip_address=ip_address,
        )

        return {
            "message": "Password changed successfully",
            "email": current_user.email,
        }

    def first_time_password_change(
        self,
        password_data: FirstTimePasswordChange,
        current_user: User,
        ip_address: str | None = None,
    ) -> dict:
        if not current_user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not required to change your password. "
                "Use the regular password change endpoint instead.",
            )

        new_hashed_password = get_password_hash(password_data.new_password)
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(
                password_hash=new_hashed_password,
                must_change_password=False,
            )
        )
        self.db.execute(stmt)
        # Now that they have a password of their own, any activation link still
        # sitting in their inbox must stop working — otherwise a forwarded
        # welcome email would remain a way into the account for three days.
        from app.services import activation_service

        activation_service.invalidate_tokens_for_user(
            self.db, current_user.id, commit=False
        )
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="first_time_password_change",
            resource_type="users",
            resource_id=current_user.id,
            details={
                "email": current_user.email,
                "first_login": True,
                "must_change_password_cleared": True,
            },
            ip_address=ip_address,
        )

        return {
            "message": "Password changed successfully. "
            "You can now use your new password for future logins.",
            "email": current_user.email,
            "must_change_password": False,
        }

    def reset_password(
        self,
        user: User,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        """Set the password chosen through a forgotten-password link.

        The link has already been spent by the caller; that is what proves
        who this is. It also counts as choosing a password of their own, so
        someone who never got round to it is no longer asked to.
        """
        from app.services import activation_service

        self.db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                password_hash=get_password_hash(new_password),
                must_change_password=False,
            )
        )
        # Every other link still in an inbox, of either kind, stops working.
        activation_service.invalidate_tokens_for_user(self.db, user.id, commit=False)
        from app.services.refresh_session_service import revoke_user_sessions
        revoke_user_sessions(self.db, user.id)
        self.db.commit()

        self.audit_service.create_audit_log(
            user_id=user.id,
            action="password_reset",
            resource_type="users",
            resource_id=user.id,
            details={"email": user.email},
            ip_address=ip_address,
        )


    def validate_bulk_csv(
        self, file_content: bytes, filename: str, entity_id: int, current_user: User
    ) -> dict:
        """Check a member file (CSV or Excel) without importing anything.

        Answers the question the import cannot: *what is wrong with this file*,
        in one pass, before a single user exists. The importer stops at the
        first problem in a row because it has nothing else to do with it; here
        every problem of every row is collected, so the file can be fixed once
        rather than by trial and error.

        Reuses the rules in ``csv_validation``, which is also what the importer
        applies. A validator that disagreed with the importer would be worse
        than none.
        """
        from app.services import csv_validation as rules

        self.auth_service.check_entity_permission(
            current_user, entity_id, "users", "create"
        )

        try:
            columns, rows = read_member_file(file_content, filename)
        except UnreadableFile as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

        if not columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío o no tiene fila de cabeceras.",
            )

        faltan = rules.missing_columns(columns)
        if faltan:
            # Without these there is nothing to check row by row.
            return {
                "filename": filename,
                "valid": False,
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "columns": columns,
                "missing_columns": faltan,
                "ignored_columns": rules.ignored_columns_present(columns),
                "unknown_columns": rules.unknown_columns(columns),
                "problems": [],
                "summary": [],
            }

        parsed = [rules.check_row(row, i) for i, row in enumerate(rows, start=2)]

        problems = [pr for row in parsed for pr in row.problems]
        problems.extend(rules.duplicates_within_file(parsed))

        # Only rows that are internally sound are worth checking against the
        # database; the rest already have to be fixed anyway.
        sanas = {r.row for r in parsed} - {pr.row for pr in problems}
        problems.extend(self._clashes_with_database(
            [r for r in parsed if r.row in sanas]
        ))

        filas_malas = {pr.row for pr in problems}
        problems.sort(key=lambda pr: (pr.row, pr.field or ""))

        # Grouped so the reader sees "206 rows with an invalid email" instead
        # of scrolling through 206 identical lines. Grouped by code, not by the
        # message: the messages quote the offending value, so no two are equal.
        resumen: dict = {}
        for pr in problems:
            resumen[pr.code] = resumen.get(pr.code, 0) + 1

        return {
            "filename": filename,
            "valid": not problems,
            "total_rows": len(parsed),
            "valid_rows": len(parsed) - len(filas_malas),
            "invalid_rows": len(filas_malas),
            "columns": columns,
            "missing_columns": [],
            "ignored_columns": rules.ignored_columns_present(columns),
            "unknown_columns": rules.unknown_columns(columns),
            "problems": [
                {
                    "row": pr.row,
                    "field": pr.field,
                    "code": pr.code,
                    "message": pr.message,
                }
                for pr in problems[:500]
            ],
            "truncated": len(problems) > 500,
            "summary": [
                {
                    "code": code,
                    "message": rules.PROBLEM_LABELS.get(code, code),
                    "count": n,
                }
                for code, n in sorted(resumen.items(), key=lambda kv: -kv[1])
            ],
        }

    def _clashes_with_database(self, parsed: list) -> list:
        """Values already taken by an existing user.

        Checked in three queries rather than one per row: a padrón of several
        hundred would otherwise mean several hundred round trips.
        """
        from app.services.csv_validation import RowProblem

        problems: list = []
        etiquetas = {"dni": "DNI", "email": "email", "phone": "teléfono"}

        for campo, etiqueta in etiquetas.items():
            valores = {getattr(r, campo): r.row for r in parsed if getattr(r, campo)}
            if not valores:
                continue
            columna = getattr(User, campo)
            existentes = self.db.execute(
                select(columna).where(columna.in_(list(valores)))
            ).scalars().all()
            for valor in existentes:
                problems.append(
                    RowProblem(
                        row=valores[valor],
                        field=campo,
                        code="already_exists",
                        message=f"Ya existe un usuario con este {etiqueta}",
                    )
                )

        return problems



def get_user_service(
    db: Session = Depends(get_sync_db),
) -> UserService:
    return UserService(db)


def process_bulk_upload_job(job_id: int, current_user_id: int, ip_address: Optional[str]) -> None:
    """
    Background task: processes a BulkUploadJob row by row, persisting progress
    to the database. Runs with its own DB session so it is decoupled from the
    HTTP request lifecycle.
    """
    from app.database import SyncSessionLocal
    from app.repositories.entity_repository import EntityRepository
    from app.services.audit_service import AuditService
    from app.services.authorization_service import AuthorizationService
    from app.services.email_service import send_welcome_email
    from app.services import activation_service
    from app.repositories.membership_repository import MembershipRepository

    with SyncSessionLocal() as db:
        job = db.execute(
            select(BulkUploadJob).where(BulkUploadJob.id == job_id)
        ).scalars().first()
        if not job:
            logger.error("BulkUploadJob %s not found", job_id)
            return

        current_user = db.execute(
            select(User).where(User.id == current_user_id)
        ).scalars().first()
        if not current_user:
            job.status = "failed"
            db.commit()
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        auth_service = AuthorizationService(db)
        audit_service = AuditService(db)
        membership_repo = MembershipRepository(db)

        errors: List[Dict[str, Any]] = []
        created_users: List[Dict[str, Any]] = []
        successful = 0
        failed = 0
        row_number = 1

        try:
            # Already read once when the job was created, so a file that got
            # this far can be read again; the filename says which format it is.
            _, rows = read_member_file(job.csv_content, job.csv_filename)
            total_rows = len(rows)
            job.total_rows = total_rows
            db.commit()

            socio_role = db.execute(
                select(Role).where(Role.name == "socio", Role.is_active == True)
            ).scalars().first()
            if not socio_role:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.error("Default 'socio' role not found")
                return

            # The association is selected in the UI and applied to every row.
            entity_id = job.target_entity_id
            target_entity = db.execute(
                select(Entity).where(Entity.id == entity_id, Entity.is_active == True)
            ).scalars().first()
            if not target_entity:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.error("Bulk upload job %s has no valid target entity", job_id)
                return
            # Permission is checked once for the selected entity.
            if not auth_service.has_effective_permission(
                current_user, entity_id, "users", "create"
            ):
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.error(
                    "User %s lacks permission to create users in entity %s",
                    current_user.id, entity_id,
                )
                return

            # The role is selected in the UI and assigned to every user.
            role_id = job.target_role_id
            role = db.execute(
                select(Role).where(Role.id == role_id, Role.is_active == True)
            ).scalars().first()
            if not role:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.error(
                    "Bulk upload job %s has no valid target role", job_id
                )
                return

            for row in rows:
                row_number += 1
                email = ""
                dni = ""
                try:
                    email = row.get("email", "").strip()
                    name = row.get("name", "").strip()
                    surname = row.get("surname", "").strip()
                    phone = row.get("phone", "").strip()
                    birthdate_str = row.get("birthdate", "").strip()
                    dni = row.get("dni", "").strip()

                    if not all([
                        name, surname,
                        birthdate_str,
                    ]):
                        raise ValueError("All required fields must be filled")

                    # Whatever lands here is read back through UserResponse,
                    # whose `email` is an EmailStr. A value that is not an
                    # address goes in without complaint and then breaks *every*
                    # listing that happens to include this user — reported by
                    # the browser as a CORS failure, because the 500 comes back
                    # without the CORS headers. Rejecting the row here turns an
                    # undiagnosable outage into one line in the error report.
                    #
                    # Spreadsheets are the usual source: an empty cell exported
                    # as "0" is not a missing email, it is a wrong one.
                    if email and not EMAIL_RE.match(email):
                        raise ValueError(
                            f"'{email}' is not a valid email address; leave the "
                            "column empty if the person has none"
                        )

                    birthdate = parse_birthdate(birthdate_str)
                    if birthdate is None:
                        raise ValueError(
                            "birthdate must be a date written as DD/MM/YYYY "
                            "or YYYY-MM-DD, with a four-digit year"
                        )

                    address = row.get("address", "").strip() or None
                    photo = row.get("photo", "").strip() or None
                    iban = row.get("iban", "").strip() or None
                    size = row.get("size", "").strip() or None
                    hobbies = row.get("hobbies", "").strip() or None
                    job_position = row.get("job_position", "").strip() or None

                    if size and size not in ALLOWED_SIZES:
                        raise ValueError(
                            f"Talla no válida '{size}'. Valores permitidos: "
                            f"{', '.join(sorted(ALLOWED_SIZES))}"
                        )

                    db_user = User(
                        email=email or None,
                        # Nobody is ever told this. They get in through the
                        # link in the welcome email and choose their own.
                        password_hash=get_password_hash(
                            generate_unusable_password()
                        ),
                        name=name,
                        surname=surname,
                        phone=phone or None,
                        address=address,
                        birthdate=birthdate,
                        dni=dni or None,
                        photo=photo,
                        iban=iban,
                        size=size,
                        hobbies=hobbies,
                        job_position=job_position,
                        is_active=True,
                        must_change_password=True,
                    )
                    db.add(db_user)
                    db.flush()

                    db.add(Membership(
                        user_id=db_user.id,
                        entity_id=entity_id,
                        role_id=role_id,
                        is_active=True,
                    ))
                    db.flush()

                    entity_repo = EntityRepository(db)
                    for parent_entity_id in entity_repo.get_parent_entity_ids(entity_id):
                        existing = membership_repo.get_by_user_and_entity(
                            db_user.id, parent_entity_id, active_only=True
                        )
                        if not existing:
                            db.add(Membership(
                                user_id=db_user.id,
                                entity_id=parent_entity_id,
                                role_id=socio_role.id,
                                is_active=True,
                            ))

                    db.commit()

                    successful += 1
                    created_users.append({
                        "id": db_user.id,
                        "email": email,
                        "name": f"{name} {surname}",
                        "entity_id": entity_id,
                        "role_id": role_id,
                    })

                    audit_service.create_audit_log(
                        user_id=current_user.id,
                        action="create",
                        resource_type="users",
                        resource_id=db_user.id,
                        details={
                            "email": email,
                            "dni": dni,
                            "name": f"{name} {surname}",
                            "bulk_upload": True,
                            "csv_row": row_number,
                            "job_id": job_id,
                        },
                        ip_address=ip_address,
                    )

                    # Same as the single-user path: the password in the CSV is
                    # the administrator's, not theirs, so the message invites
                    # them to set one through a one-shot link.
                    activation_url = None
                    if email:
                        raw_token = activation_service.issue_token(db, db_user)
                        activation_url = activation_service.build_activation_url(
                            raw_token
                        )
                    if email:
                        send_welcome_email(email, f"{name} {surname}", activation_url)

                except IntegrityError as e:
                    db.rollback()
                    failed += 1
                    error_msg = _describe_unique_clash(e)
                    errors.append({
                        "row": row_number,
                        # The column is no longer read, but older files still
                        # carry it and the error report is kept — so it stays
                        # out of what gets stored.
                        "data": {k: v for k, v in row.items() if k != "password"},
                        "error": error_msg,
                    })
                except Exception as e:
                    db.rollback()
                    failed += 1
                    # Never str(e) here. A database-level failure arrives as a
                    # SQLAlchemy error whose text embeds the whole INSERT with
                    # every bound parameter — name, address, DNI, IBAN and the
                    # password hash of a real member. That text is stored in
                    # this column and rendered in the import history, which
                    # reproduces the roster the uploaded CSV is discarded to
                    # avoid keeping. The full detail goes to the server log,
                    # where it belongs.
                    logger.exception(
                        "Bulk upload job %s failed on row %s", job_id, row_number
                    )
                    errors.append({
                        "row": row_number,
                        "error": _safe_row_error(e),
                        "data": {k: v for k, v in row.items() if k != "password"},
                    })
                finally:
                    job.processed_rows = row_number - 1
                    job.successful = successful
                    job.failed = failed
                    job.errors = errors
                    job.created_users = created_users
                    db.commit()

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            audit_service.create_audit_log(
                user_id=current_user.id,
                action="bulk_upload",
                resource_type="users",
                resource_id=None,
                details={
                    "filename": job.csv_filename,
                    "job_id": job_id,
                    "total_rows": total_rows,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": (
                        f"{(successful / total_rows * 100):.2f}%"
                        if total_rows > 0 else "0%"
                    ),
                },
                ip_address=ip_address,
            )

        except Exception:
            # logger.exception already records the traceback.
            logger.exception("Fatal error in bulk upload job %s", job_id)
            try:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                pass

        finally:
            # The uploaded CSV carries the DNI, address and IBAN of everyone
            # in it. It no longer holds passwords — those are generated now —
            # but it is still a roster of personal data, needed only while the
            # rows are being processed and previously kept in the database
            # indefinitely. Discarding it here bounds the exposure to the life
            # of the job, whether it succeeded or failed.
            try:
                job.csv_content = None
                db.commit()
            except Exception:
                logger.exception(
                    "Could not discard the stored CSV for job %s; it still "
                    "holds the personal data of everyone in it",
                    job_id,
                )
