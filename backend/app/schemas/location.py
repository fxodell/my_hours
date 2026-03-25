from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseSchema, TimestampSchema


class JobCodeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: Optional[str] = None


class LocationBase(BaseSchema):
    client_id: UUID
    region: Optional[str] = None
    site_name: str
    site_code: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    client_id: Optional[UUID] = None
    region: Optional[str] = None
    site_name: Optional[str] = None
    site_code: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase, TimestampSchema):
    id: UUID
    job_codes: list[JobCodeBrief] = Field(default_factory=list)
