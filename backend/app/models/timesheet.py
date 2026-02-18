import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.pay_period import PayPeriod
    from app.models.time_entry import TimeEntry
    from app.models.pto_entry import PTOEntry


class Timesheet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "timesheets"
    __table_args__ = (
        UniqueConstraint("employee_id", "pay_period_id", name="uq_timesheet_employee_period"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pay_periods.id", ondelete="CASCADE"),
        nullable=False,
    )

    # draft, submitted, approved, rejected
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    employee: Mapped["Employee"] = relationship(
        back_populates="timesheets",
        foreign_keys=[employee_id],
    )
    approver: Mapped[Optional["Employee"]] = relationship(
        back_populates="approved_timesheets",
        foreign_keys=[approved_by],
    )
    pay_period: Mapped["PayPeriod"] = relationship(back_populates="timesheets")
    time_entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="timesheet",
        cascade="all, delete-orphan",
    )
    pto_entries: Mapped[list["PTOEntry"]] = relationship(
        back_populates="timesheet",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Timesheet(id={self.id}, employee_id={self.employee_id}, status='{self.status}')>"
