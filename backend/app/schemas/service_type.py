from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class ServiceTypeBase(BaseSchema):
    name: str
    is_billable: bool = True
    is_active: bool = True


class ServiceTypeCreate(BaseSchema):
    name: str
    is_billable: bool = True


class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = None
    is_billable: Optional[bool] = None
    is_active: Optional[bool] = None


class ServiceTypeResponse(ServiceTypeBase, TimestampSchema):
    id: UUID
