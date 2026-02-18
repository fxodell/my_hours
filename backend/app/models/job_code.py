import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.time_entry import TimeEntry


class JobCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_codes"
    __table_args__ = (
        UniqueConstraint("location_id", "code", name="uq_job_code_location"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # AFE number
    description: Mapped[Optional[str]] = mapped_column(String(200))
    quickbooks_class_id: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    location: Mapped["Location"] = relationship(back_populates="job_codes")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="job_code")

    def __repr__(self) -> str:
        return f"<JobCode(id={self.id}, code='{self.code}')>"
