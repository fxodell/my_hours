from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class LocationBase(BaseSchema):
    client_id: UUID
    region: Optional[str] = None
    site_name: str
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    client_id: Optional[UUID] = None
    region: Optional[str] = None
    site_name: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase, TimestampSchema):
    id: UUID
