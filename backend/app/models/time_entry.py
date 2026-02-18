import uuid
from datetime import date, time
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy import String, Boolean, Date, Time, Numeric, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.timesheet import Timesheet
    from app.models.client import Client
    from app.models.location import Location
    from app.models.job_code import JobCode
    from app.models.service_type import ServiceType


class TimeEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint("hours >= 0 AND hours <= 24", name="ck_time_entry_hours_range"),
    )

    timesheet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timesheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Foreign keys to lookup tables
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        index=True,
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
    )
    job_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_codes.id"),
    )
    service_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_types.id"),
    )

    # Work details
    work_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # 'remote', 'on_site'
    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    start_time: Mapped[Optional[time]] = mapped_column(Time)
    end_time: Mapped[Optional[time]] = mapped_column(Time)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Billing and payroll flags
    is_billable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Reimbursements and bonuses (from original Excel)
    vehicle_reimbursement_tier: Mapped[Optional[str]] = mapped_column(String(50))
    bonus_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # External sync tracking
    quickbooks_time_activity_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    timesheet: Mapped["Timesheet"] = relationship(back_populates="time_entries")
    client: Mapped[Optional["Client"]] = relationship(back_populates="time_entries")
    location: Mapped[Optional["Location"]] = relationship(back_populates="time_entries")
    job_code: Mapped[Optional["JobCode"]] = relationship(back_populates="time_entries")
    service_type: Mapped[Optional["ServiceType"]] = relationship(back_populates="time_entries")

    def __repr__(self) -> str:
        return f"<TimeEntry(id={self.id}, date={self.work_date}, hours={self.hours})>"
