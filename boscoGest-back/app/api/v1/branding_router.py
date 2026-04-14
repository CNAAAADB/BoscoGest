from fastapi import APIRouter, Depends, Request, UploadFile, File, status
from app.models.user_model import User
from app.schemas.entity_branding import (
    EntityBrandingCreate,
    EntityBrandingUpdate,
    EntityBrandingResponse,
    EntityBrandingWithEntity,
)
from app.utils.auth import get_current_active_user
from app.services.branding_service import BrandingService, get_branding_service

branding_router = APIRouter(prefix="/branding", tags=["Entity Branding"])


@branding_router.get("/entity/{entity_id}", response_model=EntityBrandingResponse)
def get_entity_branding(
    entity_id: int,
    service: BrandingService = Depends(get_branding_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entity_branding(entity_id, current_user)


@branding_router.get("/subdomain/{subdomain}", response_model=EntityBrandingWithEntity)
def get_branding_by_subdomain(
    subdomain: str,
    service: BrandingService = Depends(get_branding_service),
):
    return service.get_branding_by_subdomain(subdomain)


@branding_router.post(
    "", response_model=EntityBrandingResponse, status_code=status.HTTP_201_CREATED
)
def create_branding(
    branding_in: EntityBrandingCreate,
    request: Request,
    service: BrandingService = Depends(get_branding_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_branding(
        branding_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@branding_router.put("/entity/{entity_id}", response_model=EntityBrandingResponse)
def update_branding(
    entity_id: int,
    branding_in: EntityBrandingUpdate,
    request: Request,
    service: BrandingService = Depends(get_branding_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_branding(
        entity_id,
        branding_in,
        current_user,
        ip_address=request.client.host if request else None,
    )


@branding_router.post("/entity/{entity_id}/logo", response_model=EntityBrandingResponse)
async def upload_logo(
    entity_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    service: BrandingService = Depends(get_branding_service),
    current_user: User = Depends(get_current_active_user),
):
    contents = await file.read()
    return await service.upload_logo(
        entity_id,
        file_contents=contents,
        filename=file.filename,
        content_type=file.content_type,
        current_user=current_user,
        ip_address=request.client.host if request else None,
    )


@branding_router.delete("/entity/{entity_id}", status_code=status.HTTP_200_OK)
def delete_branding(
    entity_id: int,
    request: Request,
    service: BrandingService = Depends(get_branding_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.delete_branding(
        entity_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
