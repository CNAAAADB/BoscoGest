from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session
from app.models.revoked_token_model import RevokedToken
from app.models.user_model import User
from app.utils.auth import (
    get_sync_db,
    authenticate_user,
    create_access_token,
    has_permission,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
)
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def login(
        self, email: str, password: str, ip_address: str | None = None
    ) -> dict:
        user = authenticate_user(db=self.db, email=email, password=password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Users without active memberships (e.g. pending approval) are allowed
        # to log in — the frontend handles showing the appropriate state.

        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self.audit_service.create_audit_log(
            user_id=user.id,
            action="login",
            resource_type="auth",
            details={"success": True},
            ip_address=ip_address,
        )
        return {"access_token": access_token, "token_type": "bearer"}

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
        self, current_user: User, token: str, ip_address: str | None = None
    ) -> dict:
        try:
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
