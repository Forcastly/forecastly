"""Sales and sales-import persistence models.

A sale is an aggregate: total quantity of one item at one location on one
business date. See ``docs/DATA_MODEL.md`` §24–41.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.types import CreatedAt, TimestampMixin, UUIDPrimaryKey

IMPORT_PROCESSING = "processing"
IMPORT_COMPLETED = "completed"
IMPORT_FAILED = "failed"


class SalesImport(Base):
    __tablename__ = "sales_imports"
    __table_args__ = (
        UniqueConstraint("location_id", "content_hash"),
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="status_valid",
        ),
        Index("ix_sales_imports_location_created", "location_id", "created_at"),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    accepted_row_count: Mapped[int | None] = mapped_column(Integer)
    rejected_row_count: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Sale(TimestampMixin, Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("location_id", "business_date", "item_name_normalized"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("revenue IS NULL OR revenue >= 0", name="revenue_non_negative"),
        Index("ix_sales_location_business_date", "location_id", "business_date"),
        Index(
            "ix_sales_location_item_date",
            "location_id",
            "item_name_normalized",
            "business_date",
        ),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sales_import_id: Mapped[UUID | None] = mapped_column(ForeignKey("sales_imports.id"))
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    item_name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
