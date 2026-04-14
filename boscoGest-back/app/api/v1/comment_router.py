from fastapi import APIRouter, Depends
from typing import List
from app.models.user_model import User
from app.schemas.communication import CommentCreate, CommentUpdate, CommentResponse
from app.utils.auth import get_current_active_user
from app.services.comment_service import CommentService, get_comment_service

comment_router = APIRouter(prefix="/comments", tags=["Comments"])


@comment_router.post(
    "/communications/{communication_id}/comments",
    response_model=CommentResponse,
)
def create_comment(
    communication_id: int,
    comment_in: CommentCreate,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.create_comment(communication_id, comment_in, current_user)


@comment_router.get(
    "/communications/{communication_id}/comments",
    response_model=List[CommentResponse],
)
def list_comments(
    communication_id: int,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_comments(communication_id, current_user)


@comment_router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.update_comment(comment_id, comment_in, current_user)


@comment_router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    service: CommentService = Depends(get_comment_service),
    current_user: User = Depends(get_current_active_user),
):
    return service.delete_comment(comment_id, current_user)
