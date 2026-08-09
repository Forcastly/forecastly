"""Forecast API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ForecastRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    model_version: str
    history_start_date: date | None
    history_end_date: date | None
    horizon_days: int
    generated_at: datetime


class ForecastPointSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_date: date
    item_name: str
    predicted_quantity: Decimal
    model_name: str


class GenerateForecastResponse(BaseModel):
    run: ForecastRunSchema
    forecasts: list[ForecastPointSchema]


class ForecastDayItem(BaseModel):
    item_name: str
    predicted_quantity: Decimal
    model_name: str


class ForecastDay(BaseModel):
    date: date
    items: list[ForecastDayItem]


class LatestForecastResponse(BaseModel):
    run: ForecastRunSchema
    days: list[ForecastDay]


class ForecastRunListResponse(BaseModel):
    items: list[ForecastRunSchema]
    next_cursor: str | None


class ForecastAccuracyResponse(BaseModel):
    location_id: UUID
    start_date: date | None
    end_date: date | None
    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    bias: Decimal | None


class BacktestResponse(BaseModel):
    as_of: date
    start_date: date
    end_date: date
    window_days: int
    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    bias: Decimal | None


class ModelEvaluationSchema(BaseModel):
    # `model_` is a Pydantic-protected namespace; opt out for `model_name`.
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    is_baseline: bool
    is_selected: bool
    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    rmse: Decimal | None
    bias: Decimal | None
    bias_pct: Decimal | None
    mase: Decimal | None


class ModelSelectionSchema(BaseModel):
    baseline_model: str
    challenger_model: str | None
    selected_model: str
    relative_wape_improvement: Decimal | None
    window_win_rate: Decimal | None
    reason: str


class ModelEvaluationRunResponse(BaseModel):
    id: UUID
    location_id: UUID
    horizon_days: int
    min_training_days: int
    window_step_days: int
    window_count: int
    generated_at: datetime
    models: list[ModelEvaluationSchema]
    selection: ModelSelectionSchema


class ItemChampionSchema(BaseModel):
    item_name: str
    selected_model: str
    is_override: bool  # True when the item overrides the global champion
    reason: str
    models: list[ModelEvaluationSchema]


class PerItemEvaluationResponse(BaseModel):
    location_id: UUID
    horizon_days: int
    global_champion: str
    items: list[ItemChampionSchema]
