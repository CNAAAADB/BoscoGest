from fastapi import APIRouter, Depends, Form, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.schemas.token import Token
from app.models.user_model import User
from app.utils.auth import get_current_active_user
from app.services.auth_service import AuthService, get_auth_service

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
