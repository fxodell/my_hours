import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy import String, Boolean, Date, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.timesheet import Timesheet


class Employee(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "employees"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Pay period group for staggered bi-weekly pay
    # 'A' or 'B' based on hire date
    pay_period_group: Mapped[str] = mapped_column(String(10), nullable=False)

    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # External system IDs
    engage_employee_id: Mapped[Optional[str]] = mapped_column(String(50))
    quickbooks_employee_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    timesheets: Mapped[list["Timesheet"]] = relationship(
        back_populates="employee",
        foreign_keys="Timesheet.employee_id",
    )
    approved_timesheets: Mapped[list["Timesheet"]] = relationship(
        back_populates="approver",
        foreign_keys="Timesheet.approved_by",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, email='{self.email}')>"
