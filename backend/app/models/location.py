import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.client import Client
    from app.models.job_code import JobCode
    from app.models.time_entry import TimeEntry


class Location(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "locations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    region: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "Alpine High"
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)
    site_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="locations")
    job_codes: Mapped[list["JobCode"]] = relationship(back_populates="location", cascade="all, delete-orphan")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="location")

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, site_name='{self.site_name}')>"
