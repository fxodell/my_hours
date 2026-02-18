from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class TimesheetBase(BaseSchema):
    employee_id: UUID
    pay_period_id: UUID


class TimesheetCreate(TimesheetBase):
    pass


class TimesheetUpdate(BaseModel):
    status: Optional[str] = None


class TimesheetSubmit(BaseModel):
    pass  # No fields needed, just triggers submission


class TimesheetApprove(BaseModel):
    pass  # No fields needed, just triggers approval


class TimesheetReject(BaseModel):
    rejection_reason: str


class TimesheetResponse(TimesheetBase, TimestampSchema):
    id: UUID
    status: str
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
