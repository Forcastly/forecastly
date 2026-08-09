"""Forecast persistence models.

A ``ForecastRun`` is one execution of the engine for a location; it owns many
``Forecast`` points. Historical runs are never overwritten — see
``docs/DATA_MODEL.md`` §42–52.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base
from app.core.db.types import CreatedAt, UUIDPrimaryKey

# Selection-reason values persisted on model_evaluation_runs (see app.forecasts.selection).
_SELECTION_REASONS = (
    "challenger_promoted",
    "insufficient_wape_improvement",
    "inconsistent_improvement",
    "challenger_bias_regression",
    "insufficient_history",
    "baseline_only",
)


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
    # Which model produced this point (per-item champion or fallback engine).
    model_name: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="weekday_average_v1"
    )
    created_at: Mapped[CreatedAt]

    run: Mapped[ForecastRun] = relationship(back_populates="forecasts")


class ModelEvaluationRun(Base):
    """One rolling-origin tournament for a location: config + selection outcome.

    Provides lineage — which models were compared, which was selected and why —
    with per-model results and per-window detail as children.
    """

    __tablename__ = "model_evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            f"selection_reason IN ({', '.join(repr(r) for r in _SELECTION_REASONS)})",
            name="selection_reason_valid",
        ),
        CheckConstraint("horizon_days > 0", name="eval_horizon_positive"),
        Index(
            "ix_model_evaluation_runs_location_generated",
            "location_id",
            "generated_at",
        ),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    min_training_days: Mapped[int] = mapped_column(Integer, nullable=False)
    window_step_days: Mapped[int] = mapped_column(Integer, nullable=False)
    window_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_model: Mapped[str] = mapped_column(Text, nullable=False)
    challenger_model: Mapped[str | None] = mapped_column(Text)
    selected_model: Mapped[str] = mapped_column(Text, nullable=False)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    relative_wape_improvement: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    window_win_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[CreatedAt]

    evaluations: Mapped[list[ModelEvaluationResult]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ModelEvaluationResult(Base):
    """Aggregate metrics for one model within an evaluation run."""

    __tablename__ = "model_evaluation_results"
    __table_args__ = (
        UniqueConstraint("evaluation_run_id", "model_name"),
        Index("ix_model_evaluation_results_run", "evaluation_run_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evaluated_observations: Mapped[int] = mapped_column(Integer, nullable=False)
    wape: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    mae: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    bias: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    bias_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    mase: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    is_baseline: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[CreatedAt]

    run: Mapped[ModelEvaluationRun] = relationship(back_populates="evaluations")
    windows: Mapped[list[ModelEvaluationWindow]] = relationship(
        back_populates="result",
        cascade="all, delete-orphan",
    )


class ModelEvaluationWindow(Base):
    """Per-window metrics for one model — the forecast origin and its scores."""

    __tablename__ = "model_evaluation_windows"
    __table_args__ = (Index("ix_model_evaluation_windows_result", "evaluation_result_id"),)

    id: Mapped[UUIDPrimaryKey]
    evaluation_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_evaluation_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    forecast_origin: Mapped[date] = mapped_column(Date, nullable=False)
    train_start: Mapped[date] = mapped_column(Date, nullable=False)
    train_end: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_start: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_end: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_observations: Mapped[int] = mapped_column(Integer, nullable=False)
    wape: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    mae: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    bias: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    bias_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    mase: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    created_at: Mapped[CreatedAt]

    result: Mapped[ModelEvaluationResult] = relationship(back_populates="windows")
