"""Forecast persistence models.

A ``ForecastRun`` is one execution of the engine for a location; it owns many
``Forecast`` points. Historical runs are never overwritten — see
``docs/DATA_MODEL.md`` §42–52.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base
from app.core.db.types import CreatedAt, UUIDPrimaryKey


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    __table_args__ = (
        CheckConstraint("horizon_days > 0", name="horizon_positive"),
        Index("ix_forecast_runs_location_generated", "location_id", "generated_at"),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    history_start_date: Mapped[date | None] = mapped_column(Date)
    history_end_date: Mapped[date | None] = mapped_column(Date)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[CreatedAt]

    forecasts: Mapped[list[Forecast]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("forecast_run_id", "forecast_date", "item_name_normalized"),
        CheckConstraint("predicted_quantity >= 0", name="predicted_quantity_non_negative"),
        Index("ix_forecasts_location_date", "location_id", "forecast_date"),
        Index("ix_forecasts_run", "forecast_run_id"),
        Index(
            "ix_forecasts_location_item_date",
            "location_id",
            "item_name_normalized",
            "forecast_date",
        ),
    )

    id: Mapped[UUIDPrimaryKey]
    forecast_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    item_name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    created_at: Mapped[CreatedAt]

    run: Mapped[ForecastRun] = relationship(back_populates="forecasts")
