from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.schemas.base import BaseSchema, TimestampSchema


class PTOEntryBase(BaseSchema):
    timesheet_id: UUID
    pto_date: date
    pto_type: str  # 'personal', 'sick', 'holiday', 'other'
    hours: Decimal
    notes: Optional[str] = None

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 24:
            raise ValueError("Hours must be between 0 and 24")
        return v

    @field_validator("pto_type")
    @classmethod
    def validate_pto_type(cls, v: str) -> str:
        valid_types = ("personal", "sick", "holiday", "other")
        if v not in valid_types:
            raise ValueError(f"PTO type must be one of: {', '.join(valid_types)}")
        return v


class PTOEntryCreate(BaseSchema):
    pto_date: date
    pto_type: str
    hours: Decimal
    notes: Optional[str] = None

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 24:
            raise ValueError("Hours must be between 0 and 24")
        return v

    @field_validator("pto_type")
    @classmethod
    def validate_pto_type(cls, v: str) -> str:
        valid_types = ("personal", "sick", "holiday", "other")
        if v not in valid_types:
            raise ValueError(f"PTO type must be one of: {', '.join(valid_types)}")
        return v


class PTOEntryUpdate(BaseModel):
    pto_date: Optional[date] = None
    pto_type: Optional[str] = None
    hours: Optional[Decimal] = None
    notes: Optional[str] = None


class PTOEntryResponse(PTOEntryBase, TimestampSchema):
    id: UUID
