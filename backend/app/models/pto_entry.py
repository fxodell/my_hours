import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy import String, Date, Numeric, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.timesheet import Timesheet


class PTOEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pto_entries"
    __table_args__ = (
        CheckConstraint("hours >= 0 AND hours <= 24", name="ck_pto_entry_hours_range"),
    )

    timesheet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timesheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pto_date: Mapped[date] = mapped_column(Date, nullable=False)

    # personal, sick, holiday, other
    pto_type: Mapped[str] = mapped_column(String(20), nullable=False)

    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    timesheet: Mapped["Timesheet"] = relationship(back_populates="pto_entries")

    def __repr__(self) -> str:
        return f"<PTOEntry(id={self.id}, date={self.pto_date}, type='{self.pto_type}', hours={self.hours})>"
