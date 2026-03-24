from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class CompanyBase(BaseSchema):
    name: str
    slug: str
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(TimestampSchema):
    id: UUID
    name: str
    slug: str
    is_active: bool
