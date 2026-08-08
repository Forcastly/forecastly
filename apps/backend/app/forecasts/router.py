"""Forecast HTTP routes."""

from __future__ import annotations

from datetime import date
from itertools import groupby
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import SessionDep
from app.forecasts.models import Forecast
from app.forecasts.repository import ForecastRepository
from app.forecasts.schemas import (
    ForecastAccuracyResponse,
    ForecastDay,
    ForecastDayItem,
    ForecastPointSchema,
    ForecastRunListResponse,
    ForecastRunSchema,
    GenerateForecastResponse,
    LatestForecastResponse,
)
from app.forecasts.service import ForecastService
from app.locations.repository import LocationRepository
from app.locations.service import LocationService
from app.restaurants.repository import RestaurantRepository
from app.sales.repository import SalesRepository
from app.users.dependencies import CurrentUser

router = APIRouter(tags=["forecasts"])


def get_forecast_service(session: SessionDep) -> ForecastService:
    locations = LocationService(LocationRepository(session), RestaurantRepository(session))
    return ForecastService(ForecastRepository(session), SalesRepository(session), locations)


ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]


def _group_by_day(forecasts: list[Forecast]) -> list[ForecastDay]:
    # forecasts arrive ordered by (forecast_date, item_name).
    days: list[ForecastDay] = []
    for forecast_date, group in groupby(forecasts, key=lambda f: f.forecast_date):
        items = [
            ForecastDayItem(item_name=f.item_name, predicted_quantity=f.predicted_quantity)
            for f in group
        ]
        days.append(ForecastDay(date=forecast_date, items=items))
    return days


@router.post(
    "/locations/{location_id}/forecasts",
    status_code=status.HTTP_201_CREATED,
    response_model=GenerateForecastResponse,
)
async def generate_forecast(
    location_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
) -> GenerateForecastResponse:
    run, forecasts = await service.generate(user=user, location_id=location_id)
    return GenerateForecastResponse(
        run=ForecastRunSchema.model_validate(run),
        forecasts=[ForecastPointSchema.model_validate(f) for f in forecasts],
    )


@router.get(
    "/locations/{location_id}/forecasts/latest",
    response_model=LatestForecastResponse,
)
async def latest_forecast(
    location_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
) -> LatestForecastResponse:
    run, forecasts = await service.get_latest(user, location_id)
    return LatestForecastResponse(
        run=ForecastRunSchema.model_validate(run),
        days=_group_by_day(forecasts),
    )


@router.get(
    "/locations/{location_id}/forecast-runs",
    response_model=ForecastRunListResponse,
)
async def list_forecast_runs(
    location_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> ForecastRunListResponse:
    runs, next_cursor = await service.list_runs(
        user=user, location_id=location_id, limit=limit, cursor=cursor
    )
    return ForecastRunListResponse(
        items=[ForecastRunSchema.model_validate(run) for run in runs],
        next_cursor=next_cursor,
    )


@router.get("/forecast-runs/{forecast_run_id}", response_model=GenerateForecastResponse)
async def get_forecast_run(
    forecast_run_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
) -> GenerateForecastResponse:
    run, forecasts = await service.get_run(user=user, forecast_run_id=forecast_run_id)
    return GenerateForecastResponse(
        run=ForecastRunSchema.model_validate(run),
        forecasts=[ForecastPointSchema.model_validate(f) for f in forecasts],
    )


@router.get(
    "/locations/{location_id}/forecast-accuracy",
    response_model=ForecastAccuracyResponse,
)
async def forecast_accuracy(
    location_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    item: Annotated[str | None, Query()] = None,
    forecast_run_id: Annotated[UUID | None, Query()] = None,
) -> ForecastAccuracyResponse:
    metrics = await service.accuracy(
        user=user,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
        item=item,
        forecast_run_id=forecast_run_id,
    )
    return ForecastAccuracyResponse(
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
        evaluated_observations=metrics.evaluated_observations,
        wape=metrics.wape,
        mae=metrics.mae,
        bias=metrics.bias,
    )
