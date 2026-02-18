from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class PayPeriodBase(BaseSchema):
    period_group: str
    start_date: date
    end_date: date
    payroll_run_date: Optional[date] = None
    status: str = "open"


class PayPeriodCreate(PayPeriodBase):
    pass


class PayPeriodUpdate(BaseModel):
    period_group: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    payroll_run_date: Optional[date] = None
    status: Optional[str] = None


class PayPeriodResponse(PayPeriodBase, TimestampSchema):
    id: UUID
