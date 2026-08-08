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


class GenerateForecastResponse(BaseModel):
    run: ForecastRunSchema
    forecasts: list[ForecastPointSchema]


class ForecastDayItem(BaseModel):
    item_name: str
    predicted_quantity: Decimal


class ForecastDay(BaseModel):
    date: date
    items: list[ForecastDayItem]


class LatestForecastResponse(BaseModel):
    run: ForecastRunSchema
    days: list[ForecastDay]


class ForecastAccuracyResponse(BaseModel):
    location_id: UUID
    start_date: date | None
    end_date: date | None
    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    bias: Decimal | None
