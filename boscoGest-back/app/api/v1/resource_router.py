from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, Query, status
from fastapi.responses import RedirectResponse
from typing import List, Optional
from app.models.resource_model import ResourceType
from app.models.user_model import User
from app.schemas.resource import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceDetails,
    ResourceCategoryCreate,
    ResourceCategoryUpdate,
    ResourceCategoryResponse,
)
from app.utils.auth import get_current_active_user
from app.services.resource_service import (
    ResourceService,
    ResourceCategoryService,
    get_resource_service,
    get_resource_category_service,
)

resource_router = APIRouter(prefix="/resources", tags=["Resource Management"])
category_router = APIRouter(
    prefix="/resource-categories", tags=["Resource Categories"]
)


# =====================
# Resource Category CRUD
# =====================


@category_router.post(
    "",
    response_model=ResourceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category: ResourceCategoryCreate,
    request: Request = None,
    service: ResourceCategoryService = Depends(get_resource_category_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_category(
        category,
        current_user,
        ip_address=request.client.host if request else None,
    )


@category_router.get("", response_model=List[ResourceCategoryResponse])
def list_categories(
    entity_id: int = Query(...),
    service: ResourceCategoryService = Depends(get_resource_category_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_categories(entity_id, current_user)


@category_router.put(
    "/{category_id}", response_model=ResourceCategoryResponse
)
def update_category(
    category_id: int,
    category_update: ResourceCategoryUpdate,
    request: Request = None,
    service: ResourceCategoryService = Depends(get_resource_category_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_category(
        category_id,
        category_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@category_router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_category(
    category_id: int,
    request: Request = None,
    service: ResourceCategoryService = Depends(get_resource_category_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_category(
        category_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return None


# =====================
# Resource CRUD
# =====================


@resource_router.post(
    "/link",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource_link(
    resource: ResourceCreate,
    request: Request = None,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_resource_link(
        resource,
        current_user,
        ip_address=request.client.host if request else None,
    )


@resource_router.post(
    "", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED
)
async def create_resource_file(
    title: str = Form(...),
    resource_type: ResourceType = Form(...),
    entity_id: int = Form(...),
    description: str = Form(None),
    tags: str = Form(None),
    category_id: int = Form(None),
    file: UploadFile = File(...),
    request: Request = None,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    content = await file.read()
    return await service.create_resource_file(
        title=title,
        resource_type=resource_type,
        entity_id=entity_id,
        file_contents=content,
        filename=file.filename,
        content_type=file.content_type,
        current_user=current_user,
        description=description,
        tags=tags,
        category_id=category_id,
        ip_address=request.client.host if request else None,
    )


@resource_router.get("", response_model=List[ResourceDetails])
def list_resources(
    entity_id: Optional[int] = None,
    category_id: Optional[int] = None,
    resource_type: Optional[ResourceType] = Query(None, alias="type"),
    tags: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_resources(
        current_user,
        entity_id=entity_id,
        category_id=category_id,
        resource_type=resource_type,
        tags=tags,
        search=search,
        skip=skip,
        limit=limit,
    )


@resource_router.get("/{resource_id}", response_model=ResourceDetails)
def get_resource(
    resource_id: int,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_resource(resource_id, current_user)


@resource_router.get("/{resource_id}/file")
def get_resource_file(
    resource_id: int,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    url = service.get_resource_file_url(resource_id, current_user)
    return RedirectResponse(url=url)


@resource_router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: int,
    resource_update: ResourceUpdate,
    request: Request = None,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_resource(
        resource_id,
        resource_update,
        current_user,
        ip_address=request.client.host if request else None,
    )


@resource_router.delete(
    "/{resource_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_resource(
    resource_id: int,
    request: Request = None,
    service: ResourceService = Depends(get_resource_service),
    current_user: User = Depends(get_current_active_user),
):
    service.delete_resource(
        resource_id,
        current_user,
        ip_address=request.client.host if request else None,
    )
    return None
