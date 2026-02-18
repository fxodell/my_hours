from datetime import date, time
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.schemas.base import BaseSchema, TimestampSchema


class TimeEntryBase(BaseSchema):
    timesheet_id: UUID
    work_date: date
    client_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    job_code_id: Optional[UUID] = None
    service_type_id: Optional[UUID] = None
    work_mode: str  # 'remote' or 'on_site'
    hours: Decimal
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    description: Optional[str] = None
    is_billable: bool = True
    is_overtime: bool = False
    vehicle_reimbursement_tier: Optional[str] = None
    bonus_eligible: bool = False

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 24:
            raise ValueError("Hours must be between 0 and 24")
        return v

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: str) -> str:
        if v not in ("remote", "on_site"):
            raise ValueError("Work mode must be 'remote' or 'on_site'")
        return v


class TimeEntryCreate(BaseSchema):
    work_date: date
    client_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    job_code_id: Optional[UUID] = None
    service_type_id: Optional[UUID] = None
    work_mode: str
    hours: Decimal
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    description: Optional[str] = None
    is_billable: bool = True
    is_overtime: bool = False
    vehicle_reimbursement_tier: Optional[str] = None
    bonus_eligible: bool = False

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 24:
            raise ValueError("Hours must be between 0 and 24")
        return v

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: str) -> str:
        if v not in ("remote", "on_site"):
            raise ValueError("Work mode must be 'remote' or 'on_site'")
        return v


class TimeEntryUpdate(BaseModel):
    work_date: Optional[date] = None
    client_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    job_code_id: Optional[UUID] = None
    service_type_id: Optional[UUID] = None
    work_mode: Optional[str] = None
    hours: Optional[Decimal] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    description: Optional[str] = None
    is_billable: Optional[bool] = None
    is_overtime: Optional[bool] = None
    vehicle_reimbursement_tier: Optional[str] = None
    bonus_eligible: Optional[bool] = None


class TimeEntryResponse(TimeEntryBase, TimestampSchema):
    id: UUID
