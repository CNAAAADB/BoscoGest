from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class EntityBase(BaseModel):
    name: str
    level: int
    parent_id: Optional[int] = None


class EntityCreate(BaseModel):
    name: str
    parent_id: int  # Obligatorio: ID de la entidad padre


class EntityUpdate(BaseModel):
    name: Optional[str] = None
    # parent_id y level no se pueden modificar una vez creada la entidad


class EntityResponse(EntityBase):
    id: int
    is_active: bool = True
    created_at: datetime
    parent: Optional["EntityResponse"] = None  # self-referential relationship

    model_config = ConfigDict(from_attributes=True)


class EntityDetails(EntityResponse):
    children: List["EntityResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# Rebuild forward references for self-relations
EntityResponse.model_rebuild()
EntityDetails.model_rebuild()