from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    id: UUID
