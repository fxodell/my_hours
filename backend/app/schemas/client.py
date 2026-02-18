from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class ClientBase(BaseSchema):
    name: str
    industry: Optional[str] = None
    quickbooks_customer_id: Optional[str] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    quickbooks_customer_id: Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase, TimestampSchema):
    id: UUID
