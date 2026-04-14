from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, status
from fastapi.responses import RedirectResponse
from typing import List
from app.models.user_model import User
from app.schemas.magazine import MagazineResponse, MagazineUpdate, MagazineDetails
from app.utils.auth import get_current_active_user
from app.services.magazine_service import MagazineService, get_magazine_service

magazine_router = APIRouter(prefix="/magazines", tags=["Magazine Management"])


@magazine_router.post(
    "", response_model=MagazineResponse, status_code=status.HTTP_201_CREATED
)
async def create_magazine(
    title: str = Form(...),
    collection: str = Form(None),
    issue_number: str = Form(None),
    description: str = Form(None),
    entity_id: int = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    content = await file.read()
    return await service.create_magazine(
        title=title,
        entity_id=entity_id,
        file_contents=content,
        filename=file.filename,
        current_user=current_user,
        collection=collection,
        issue_number=issue_number,
        description=description,
        ip_address=request.client.host if request else None,
    )


@magazine_router.get("", response_model=List[MagazineDetails])
def get_magazines(
    skip: int = 0,
    limit: int = 100,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_magazines(current_user, skip=skip, limit=limit)


@magazine_router.get("/{magazine_id}", response_model=MagazineDetails)
def get_magazine(
    magazine_id: int,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_magazine(magazine_id, current_user)


@magazine_router.get("/{magazine_id}/file")
def get_magazine_file(
    magazine_id: int,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    url = service.get_magazine_file_url(magazine_id, current_user)
    return RedirectResponse(url=url)


@magazine_router.put("/{magazine_id}", response_model=MagazineResponse)
def update_magazine(
    magazine_id: int,
    magazine_update: MagazineUpdate,
    request: Request = None,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_magazine(
        magazine_id,
        magazine_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@magazine_router.delete("/{magazine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_magazine(
    magazine_id: int,
    request: Request = None,
    service: MagazineService = Depends(get_magazine_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_magazine(
        magazine_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return None
