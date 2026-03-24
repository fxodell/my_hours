import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.timesheet import Timesheet


class BillingWeek(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "billing_weeks"
    __table_args__ = (
        UniqueConstraint("timesheet_id", "week_start_date", name="uq_billing_week_timesheet_start"),
    )

    timesheet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timesheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # open, submitted, approved, billed, reopened
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
    )
    billed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    timesheet: Mapped["Timesheet"] = relationship(back_populates="billing_weeks")
    approver: Mapped[Optional["Employee"]] = relationship(foreign_keys=[approved_by])

    def __repr__(self) -> str:
        return (
            f"<BillingWeek(id={self.id}, timesheet_id={self.timesheet_id}, "
            f"start={self.week_start_date}, end={self.week_end_date}, status={self.status})>"
        )
