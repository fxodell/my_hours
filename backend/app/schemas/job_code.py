from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class JobCodeBase(BaseSchema):
    location_id: UUID
    code: str
    description: Optional[str] = None
    quickbooks_class_id: Optional[str] = None
    is_active: bool = True


class JobCodeCreate(JobCodeBase):
    pass


class JobCodeUpdate(BaseModel):
    location_id: Optional[UUID] = None
    code: Optional[str] = None
    description: Optional[str] = None
    quickbooks_class_id: Optional[str] = None
    is_active: Optional[bool] = None


class JobCodeResponse(JobCodeBase, TimestampSchema):
    id: UUID
