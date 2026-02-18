from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.schemas.base import BaseSchema, TimestampSchema


class EmployeeBase(BaseSchema):
    email: EmailStr
    first_name: str
    last_name: str
    hire_date: date
    pay_period_group: str
    hourly_rate: Optional[Decimal] = None
    is_manager: bool = False
    is_admin: bool = False
    is_active: bool = True
    engage_employee_id: Optional[str] = None
    quickbooks_employee_id: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    password: str


class EmployeeUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hire_date: Optional[date] = None
    pay_period_group: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    is_manager: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    engage_employee_id: Optional[str] = None
    quickbooks_employee_id: Optional[str] = None
    password: Optional[str] = None


class EmployeeResponse(TimestampSchema):
    """Response schema - uses str for email to avoid validation on output."""
    id: UUID
    email: str  # Use str instead of EmailStr to allow .local domains
    first_name: str
    last_name: str
    hire_date: date
    pay_period_group: str
    hourly_rate: Optional[Decimal] = None
    is_manager: bool
    is_admin: bool
    is_active: bool
    engage_employee_id: Optional[str] = None
    quickbooks_employee_id: Optional[str] = None
    full_name: str


class EmployeeLogin(BaseModel):
    email: EmailStr
    password: str
