from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class ServiceTypeBase(BaseSchema):
    name: str
    is_billable: bool = True


class ServiceTypeCreate(ServiceTypeBase):
    pass


class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = None
    is_billable: Optional[bool] = None


class ServiceTypeResponse(ServiceTypeBase, TimestampSchema):
    id: UUID
