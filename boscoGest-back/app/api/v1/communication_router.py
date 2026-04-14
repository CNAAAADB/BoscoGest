from fastapi import APIRouter, Depends, UploadFile, File, Query
from typing import List, Optional
from app.models.user_model import User
from app.schemas.entity import EntityResponse
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationUpdate,
    CommunicationResponse,
    CommunicationWithCommentsResponse,
    StatusTransitionRequest,
)
from app.utils.auth import get_current_active_user
from app.services.communication_service import (
    CommunicationService,
    get_communication_service,
)

communication_router = APIRouter(
    prefix="/communications", tags=["Communications"]
)


@communication_router.get(
    "/entities-with-permissions", response_model=List[EntityResponse]
)
def get_entities_with_create_permission(
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entities_with_create_permission(current_user)


@communication_router.post("", response_model=CommunicationResponse)
def create_communication(
    communication_in: CommunicationCreate,
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_communication(communication_in, current_user)


@communication_router.get("", response_model=List[CommunicationResponse])
def list_communications(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = Query(None, description="Filter by status"),
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_communications(current_user, skip=skip, limit=limit, status=status)


@communication_router.get("/count")
def count_communications(
    status: Optional[str] = Query(None, description="Filter by status"),
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.count_communications(current_user, status=status)


@communication_router.get(
    "/{communication_id}", response_model=CommunicationWithCommentsResponse
)
def get_communication(
    communication_id: int,
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_communication(communication_id, current_user)


@communication_router.put(
    "/{communication_id}", response_model=CommunicationResponse
)
def update_communication(
    communication_id: int,
    communication_in: CommunicationUpdate,
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_communication(
        communication_id, communication_in, current_user
    )


@communication_router.patch(
    "/{communication_id}/status", response_model=CommunicationResponse
)
def transition_status(
    communication_id: int,
    transition: StatusTransitionRequest,
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.transition_status(
        communication_id, transition.target_status.value, current_user
    )


@communication_router.delete("/{communication_id}")
def delete_communication(
    communication_id: int,
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.delete_communication(communication_id, current_user)


@communication_router.post("/{communication_id}/upload-image")
def upload_communication_image(
    communication_id: int,
    file: UploadFile = File(...),
    service: CommunicationService = Depends(get_communication_service),
    current_user: User = Depends(get_current_active_user),
):
    content = file.file.read()
    return service.upload_image(
        communication_id,
        file_contents=content,
        filename=file.filename,
        content_type=file.content_type,
        current_user=current_user,
    )
