from datetime import datetime
from fastapi import Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session
from app.models.revoked_token_model import RevokedToken
from app.models.user_model import User
from app.utils.auth import (
    get_sync_db,
    authenticate_user,
    has_permission,
    SECRET_KEY,
    ALGORITHM,
)
from app.services.audit_service import AuditService
from app.services.refresh_session_service import create_session, revoke_session


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def login(
        self, identifier: str, password: str, ip_address: str | None = None
    ) -> dict:
        # identifier puede ser email o teléfono
        user = authenticate_user(db=self.db, identifier=identifier, password=password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Users without active memberships (e.g. pending approval) are allowed
        # to log in — the frontend handles showing the appropriate state.

        return self.session_for(user, ip_address=ip_address, method="password")

    def session_for(
        self,
        user: User,
        ip_address: str | None = None,
        method: str = "password",
    ) -> dict:
        """Open a session for a user whose identity is already settled.

        Shared by the password login and by the one-shot links from welcome
        emails, so both produce the same kind of session and both leave the
        same trace. ``method`` is what tells them apart in the audit log.
        """
        access_token, refresh_token = create_session(self.db, user)
        self.audit_service.create_audit_log(
            user_id=user.id,
            action="login",
            resource_type="auth",
            details={"success": True, "method": method},
            ip_address=ip_address,
        )
        return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

    def check_permission(
        self,
        current_user: User,
        resource: str,
        action: str,
        resource_id: int | None = None,
        ip_address: str | None = None,
    ) -> dict:
        context = {
            "current_time": datetime.now().time(),
            "ip_address": ip_address,
        }
        has_access = has_permission(
            user=current_user,
            resource=resource,
            action=action,
            resource_id=resource_id,
            context=context,
        )
        return {"has_permission": has_access}

    def logout(
        self, current_user: User, token: str, ip_address: str | None = None,
        refresh_token: str | None = None,
    ) -> dict:
        try:
            revoke_session(self.db, refresh_token)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                revoked_token = RevokedToken(
                    jti=jti, expires_at=datetime.fromtimestamp(exp)
                )
                self.db.add(revoked_token)
                self.db.commit()

            self.audit_service.create_audit_log(
                user_id=current_user.id,
                action="logout",
                resource_type="auth",
                details={"success": True, "jti": jti},
                ip_address=ip_address,
            )
            return {"message": "Successfully logged out"}
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Logout failed: {str(e)}"
            )


def get_auth_service(db: Session = Depends(get_sync_db)) -> AuthService:
    return AuthService(db)
