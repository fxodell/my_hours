import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.time_entry import TimeEntry


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(50))  # O&G, Fiber, Power, Water, Data, Admin
    quickbooks_customer_id: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    locations: Mapped[list["Location"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}')>"
