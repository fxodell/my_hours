import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.location import Location
    from app.models.time_entry import TimeEntry


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_client_company_name"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(50))  # O&G, Fiber, Power, Water, Data, Admin
    quickbooks_customer_id: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    locations: Mapped[list["Location"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}')>"
