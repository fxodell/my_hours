import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.client import Client
    from app.models.location import Location
    from app.models.job_code import JobCode


class SiteRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "site_requests"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(100))
    job_code: Mapped[Optional[str]] = mapped_column(String(50))
    job_code_description: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    created_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
    )
    created_job_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_codes.id"),
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])
    client: Mapped["Client"] = relationship()
    reviewer: Mapped[Optional["Employee"]] = relationship(foreign_keys=[reviewed_by])
    created_location: Mapped[Optional["Location"]] = relationship()
    created_job_code: Mapped[Optional["JobCode"]] = relationship()

    def __repr__(self) -> str:
        return f"<SiteRequest(id={self.id}, site_name='{self.site_name}', status='{self.status}')>"
