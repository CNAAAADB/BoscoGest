from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.comment_model import Comment
from app.repositories.base_repository import BaseRepository


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db
        self.base = BaseRepository(db, Comment)

    def get_by_id(self, comment_id: int) -> Optional[Comment]:
        return self.base.get_by_id(comment_id)

    def get_by_communication_id(self, communication_id: int) -> List[Comment]:
        return self.base.get_all(
            filters={"communication_id": communication_id},
            order_by=Comment.created_at.desc(),
        )

    def create(self, comment: Comment) -> Comment:
        return self.base.create(comment)

    def hard_delete(self, comment: Comment) -> None:
        self.base.hard_delete(comment)
