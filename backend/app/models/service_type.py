import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.time_entry import TimeEntry


class ServiceType(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "service_types"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_service_type_company_name"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_billable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="service_type")

    def __repr__(self) -> str:
        return f"<ServiceType(id={self.id}, name='{self.name}')>"
