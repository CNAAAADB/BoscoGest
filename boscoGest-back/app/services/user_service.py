from typing import List, Dict, Any
from datetime import datetime
import csv
import io
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, update
from app.models.user_model import User
from app.models.membership_model import Membership
from app.models.entity_model import Entity
from app.models.role_model import Role
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PasswordChange,
    FirstTimePasswordChange,
)
from app.repositories.user_repository import UserRepository
from app.repositories.membership_repository import MembershipRepository
from app.services.membership_service import MembershipService
from app.services.authorization_service import AuthorizationService
from app.services.audit_service import AuditService
from app.utils.auth import get_sync_db, get_password_hash, verify_password


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

            hashed_password = get_password_hash(user_in.password)

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

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or DNI already exists",
            )

    def get_managed_users(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        accessible_entity_ids = self.auth_service.get_accessible_entity_ids(
            current_user
        )
        if not accessible_entity_ids:
            return []

        users = self.user_repo.get_by_entity_ids(
            accessible_entity_ids, skip=skip, limit=limit
        )
        return [UserResponse.model_validate(u) for u in users]

    def get_users(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        accessible_entity_ids = self.auth_service.get_accessible_entity_ids(
            current_user
        )
        if not accessible_entity_ids:
            return []

        users = self.user_repo.get_by_entity_ids(
            accessible_entity_ids, skip=skip, limit=limit
        )
        return [UserResponse.model_validate(u) for u in users]

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

        update_data = user_update.model_dump(exclude_unset=True)
        # JSON-safe copy for the audit log (datetime.date is not JSON-serialisable)
        audit_data = user_update.model_dump(exclude_unset=True, mode="json")
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

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or DNI already exists",
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

    def bulk_upload_users(
        self,
        file_content: bytes,
        filename: str,
        current_user: User,
        ip_address: str | None = None,
    ) -> Dict[str, Any]:
        if not filename.endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file",
            )

        try:
            decoded_content = file_content.decode("utf-8-sig")
            csv_reader = csv.DictReader(
                io.StringIO(decoded_content),
                quoting=csv.QUOTE_ALL,
                skipinitialspace=True,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading CSV file: {str(e)}",
            )

        required_columns = [
            "email", "password", "name", "surname", "phone",
            "birthdate", "dni", "entity_id", "role_id",
        ]
        csv_columns = csv_reader.fieldnames or []
        missing_columns = [
            col for col in required_columns if col not in csv_columns
        ]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}",
            )

        socio_role = self.db.execute(
            select(Role).where(Role.name == "socio", Role.is_active == True)
        ).scalars().first()
        if not socio_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default 'socio' role not found in the system",
            )

        results: Dict[str, Any] = {
            "total_rows": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
            "created_users": [],
        }

        row_number = 1

        for row in csv_reader:
            row_number += 1
            results["total_rows"] += 1

            try:
                email = row.get("email", "").strip()
                password = row.get("password", "").strip()
                name = row.get("name", "").strip()
                surname = row.get("surname", "").strip()
                phone = row.get("phone", "").strip()
                birthdate_str = row.get("birthdate", "").strip()
                dni = row.get("dni", "").strip()
                entity_id_str = row.get("entity_id", "").strip()
                role_id_str = row.get("role_id", "").strip()

                if not all([
                    email, password, name, surname, phone,
                    birthdate_str, dni, entity_id_str, role_id_str,
                ]):
                    raise ValueError("All required fields must be filled")

                try:
                    entity_id = int(entity_id_str)
                    role_id = int(role_id_str)
                except ValueError:
                    raise ValueError(
                        "entity_id and role_id must be valid integers"
                    )

                try:
                    birthdate = datetime.strptime(
                        birthdate_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    raise ValueError(
                        "birthdate must be in format YYYY-MM-DD"
                    )

                if len(password) < 8:
                    raise ValueError(
                        "Password must be at least 8 characters"
                    )
                if not any(char.isdigit() for char in password):
                    raise ValueError(
                        "Password must contain at least one digit"
                    )
                if not any(char.isupper() for char in password):
                    raise ValueError(
                        "Password must contain at least one uppercase letter"
                    )

                entity = self.db.execute(
                    select(Entity).where(
                        Entity.id == entity_id, Entity.is_active == True
                    )
                ).scalars().first()
                if not entity:
                    raise ValueError(
                        f"Entity with id {entity_id} not found or inactive"
                    )

                role = self.db.execute(
                    select(Role).where(
                        Role.id == role_id, Role.is_active == True
                    )
                ).scalars().first()
                if not role:
                    raise ValueError(
                        f"Role with id {role_id} not found or inactive"
                    )

                self.auth_service.check_entity_permission(
                    current_user, entity_id, "users", "create"
                )

                address = row.get("address", "").strip() or None
                photo = row.get("photo", "").strip() or None
                iban = row.get("iban", "").strip() or None
                size = row.get("size", "").strip() or None
                hobbies = row.get("hobbies", "").strip() or None
                job_position = row.get("job_position", "").strip() or None

                hashed_password = get_password_hash(password)

                db_user = User(
                    email=email,
                    password_hash=hashed_password,
                    name=name,
                    surname=surname,
                    phone=phone,
                    address=address,
                    birthdate=birthdate,
                    dni=dni,
                    photo=photo,
                    iban=iban,
                    size=size,
                    hobbies=hobbies,
                    job_position=job_position,
                    is_active=True,
                    must_change_password=True,
                )
                self.db.add(db_user)
                self.db.flush()

                membership = Membership(
                    user_id=db_user.id,
                    entity_id=entity_id,
                    role_id=role_id,
                    is_active=True,
                )
                self.db.add(membership)
                self.db.flush()

                # Create parent entity memberships (consolidated logic)
                from app.repositories.entity_repository import EntityRepository
                entity_repo = EntityRepository(self.db)
                parent_entity_ids = entity_repo.get_parent_entity_ids(entity_id)

                for parent_entity_id in parent_entity_ids:
                    existing = self.membership_repo.get_by_user_and_entity(
                        db_user.id, parent_entity_id, active_only=True
                    )
                    if not existing:
                        parent_membership = Membership(
                            user_id=db_user.id,
                            entity_id=parent_entity_id,
                            role_id=socio_role.id,
                            is_active=True,
                        )
                        self.db.add(parent_membership)

                self.db.commit()

                results["successful"] += 1
                results["created_users"].append({
                    "id": db_user.id,
                    "email": email,
                    "name": f"{name} {surname}",
                    "entity_id": entity_id,
                    "role_id": role_id,
                })

                self.audit_service.create_audit_log(
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
                    },
                    ip_address=ip_address,
                )

            except IntegrityError as e:
                self.db.rollback()
                results["failed"] += 1
                error_msg = "Email or DNI already exists"
                if "email" in str(e.orig):
                    error_msg = f"Email '{email}' already exists"
                elif "dni" in str(e.orig):
                    error_msg = f"DNI '{dni}' already exists"
                results["errors"].append({
                    "row": row_number,
                    "error": error_msg,
                    "data": {
                        k: v for k, v in row.items() if k != "password"
                    },
                })

            except Exception as e:
                self.db.rollback()
                results["failed"] += 1
                results["errors"].append({
                    "row": row_number,
                    "error": str(e),
                    "data": {
                        k: v for k, v in row.items() if k != "password"
                    },
                })

        self.audit_service.create_audit_log(
            user_id=current_user.id,
            action="bulk_upload",
            resource_type="users",
            resource_id=None,
            details={
                "filename": filename,
                "total_rows": results["total_rows"],
                "successful": results["successful"],
                "failed": results["failed"],
                "success_rate": (
                    f"{(results['successful'] / results['total_rows'] * 100):.2f}%"
                    if results["total_rows"] > 0
                    else "0%"
                ),
            },
            ip_address=ip_address,
        )

        return results

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


def get_user_service(
    db: Session = Depends(get_sync_db),
) -> UserService:
    return UserService(db)
