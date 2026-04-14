from datetime import date
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.token import Token
from app.schemas.membership_request import RegisterRequest, MembershipRequestResponse
from app.models.user_model import User
from app.utils.auth import (
    get_current_active_user,
    get_sync_db,
    get_password_hash,
)
from app.services.auth_service import AuthService, get_auth_service
from app.services.membership_request_service import MembershipRequestService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/token", response_model=Token)
def login_for_access_token(
    email: str = Form(...),
    password: str = Form(...),
    request: Request = None,
    service: AuthService = Depends(get_auth_service),
):
    ip_address = request.client.host if request else None
    return service.login(email, password, ip_address=ip_address)


@auth_router.get("/check-permission")
def check_user_permission(
    resource: str,
    action: str,
    resource_id: Optional[int] = None,
    request: Request = None,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user),
):
    ip_address = request.client.host if request else None
    return service.check_permission(
        current_user, resource, action, resource_id, ip_address=ip_address
    )


@auth_router.post("/logout")
def logout(
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
    request: Request = None,
):
    ip_address = request.client.host if request else None
    return service.logout(current_user, token, ip_address=ip_address)


@auth_router.post(
    "/register",
    response_model=MembershipRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    register_in: RegisterRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Public endpoint: create a user account and submit a membership request.
    The user can log in immediately but has no permissions until an admin accepts.
    """
    # Check email uniqueness
    existing = db.execute(
        select(User).where(User.email == register_in.email)
    ).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email",
        )

    # Create user account
    new_user = User(
        name=register_in.name,
        surname=register_in.surname,
        email=register_in.email,
        password_hash=get_password_hash(register_in.password),
        phone=register_in.phone,
        birthdate=date.fromisoformat(register_in.birthdate),
        dni=register_in.dni,
        address=register_in.address,
        is_active=True,
        must_change_password=False,
    )
    db.add(new_user)
    db.flush()

    # Create membership request
    request_service = MembershipRequestService(db)
    req = request_service.create_request(
        user_id=new_user.id,
        entity_id=register_in.entity_id,
        message=register_in.message,
    )

    return req
