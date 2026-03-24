import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.timesheet import Timesheet


class PayPeriod(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pay_periods"
    __table_args__ = (
        UniqueConstraint("company_id", "period_group", "start_date", name="uq_pay_period_company_group_start"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_group: Mapped[str] = mapped_column(String(10), nullable=False)  # 'A' or 'B'
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    payroll_run_date: Mapped[Optional[date]] = mapped_column(Date)

    # open, closed, processed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    # Relationships
    timesheets: Mapped[list["Timesheet"]] = relationship(back_populates="pay_period")

    def __repr__(self) -> str:
        return f"<PayPeriod(id={self.id}, group='{self.period_group}', start={self.start_date})>"
