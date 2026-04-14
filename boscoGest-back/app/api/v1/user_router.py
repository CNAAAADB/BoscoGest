from fastapi import APIRouter, Depends, Request, Response, UploadFile, File, status
from typing import List, Dict, Any
from app.models.user_model import User
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    UserDetails,
    PasswordChange,
    FirstTimePasswordChange,
)
from app.utils.auth import require_permission, get_current_active_user
from app.services.user_service import UserService, get_user_service

user_router = APIRouter(prefix="/users", tags=["User Management"])


@user_router.post("", response_model=UserResponse)
def create_user(
    user: UserCreate,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_user(
        user,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.get("/managed", response_model=List[UserResponse])
def get_managed_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "manage")),
):
    return service.get_managed_users(current_user, skip=skip, limit=limit)


@user_router.get("", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "list")),
):
    return service.get_users(current_user, skip=skip, limit=limit)


@user_router.get("/search/email/{email}", response_model=UserResponse)
def search_user_by_email(
    email: str,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    return service.search_by_email(email)


@user_router.get("/search/dni/{dni}", response_model=UserResponse)
def search_user_by_dni(
    dni: str,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    return service.search_by_dni(dni)


@user_router.get("/{user_id}", response_model=UserDetails)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "read")),
):
    return service.get_user(user_id)


@user_router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "update")),
):
    return service.update_user(
        user_id,
        user_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_permission("users", "delete")),
):
    service.delete_user(
        user_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.post("/bulk-upload", response_model=Dict[str, Any])
def bulk_upload_users(
    file: UploadFile = File(...),
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    content = file.file.read()
    return service.bulk_upload_users(
        content,
        file.filename,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: PasswordChange,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.change_password(
        password_data,
        current_user,
        ip_address=request.client.host if request else None,
    )


@user_router.post(
    "/first-time-password-change", status_code=status.HTTP_200_OK
)
def first_time_password_change(
    password_data: FirstTimePasswordChange,
    request: Request = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.first_time_password_change(
        password_data,
        current_user,
        ip_address=request.client.host if request else None,
    )
