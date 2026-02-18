from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.time_entry import TimeEntry


class ServiceType(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "service_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_billable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="service_type")

    def __repr__(self) -> str:
        return f"<ServiceType(id={self.id}, name='{self.name}')>"
