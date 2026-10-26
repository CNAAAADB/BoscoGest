from fastapi import APIRouter, Depends, UploadFile, File
from app.models.user_model import User
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from app.schemas.activity_registration import ActivityRegistrationOut
from app.schemas.entity import EntityResponse
from app.utils.auth import get_current_active_user
from app.services.activity_service import ActivityService, get_activity_service

activity_router = APIRouter(prefix="/activities", tags=["Activities"])


@activity_router.get(
    "/entities-with-permissions", response_model=list[EntityResponse]
)
def get_entities_with_create_permission(
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_entities_with_create_permission(current_user)


@activity_router.post("", response_model=ActivityResponse)
def create_activity(
    activity_in: ActivityCreate,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_activity(activity_in, current_user)


@activity_router.get("", response_model=list[ActivityResponse])
def list_activities(
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_activities(current_user)


@activity_router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
):
    return service.get_activity(activity_id)


@activity_router.put("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_in: ActivityUpdate,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_activity(activity_id, activity_in, current_user)


@activity_router.delete("/{activity_id}")
def delete_activity(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.delete_activity(activity_id, current_user)


@activity_router.post(
    "/{activity_id}/register", response_model=ActivityRegistrationOut
)
def register_activity(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.register_activity(activity_id, current_user)


@activity_router.get(
    "/{activity_id}/my-registration",
    response_model=ActivityRegistrationOut | None,
)
def get_my_registration(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_my_registration(activity_id, current_user)


@activity_router.get(
    "/{activity_id}/registrations",
    response_model=list[ActivityRegistrationOut],
)
def list_registrations(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_registrations(activity_id, current_user)


@activity_router.post(
    "/{activity_id}/registrations/{user_id}/accept",
    response_model=ActivityRegistrationOut,
)
def accept_registration(
    activity_id: int,
    user_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.accept_registration(activity_id, user_id, current_user)


@activity_router.post(
    "/{activity_id}/registrations/{user_id}/reject",
    response_model=ActivityRegistrationOut,
)
def reject_registration(
    activity_id: int,
    user_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.reject_registration(activity_id, user_id, current_user)


@activity_router.post("/{activity_id}/chat-group")
def create_activity_chat_group(
    activity_id: int,
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    """Create a chat group with all admitted participants of the activity."""
    return service.create_chat_group(activity_id, current_user)


@activity_router.post("/{activity_id}/upload-image")
def upload_activity_image(
    activity_id: int,
    file: UploadFile = File(...),
    service: ActivityService = Depends(get_activity_service),
    current_user: User = Depends(get_current_active_user),
):
    content = file.file.read()
    return service.upload_image(
        activity_id,
        file_contents=content,
        filename=file.filename,
        content_type=file.content_type,
        current_user=current_user,
    )
