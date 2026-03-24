from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class BillingWeekResponse(TimestampSchema):
    id: UUID
    timesheet_id: UUID
    week_start_date: date
    week_end_date: date
    status: str
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    billed_at: Optional[datetime] = None


class BillingWeekStatusUpdate(BaseSchema):
    status: str
