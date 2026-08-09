"""Forecast HTTP routes."""

from __future__ import annotations

from datetime import date
from itertools import groupby
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import SessionDep
from app.forecasts.models import Forecast, ModelEvaluationRun
from app.forecasts.repository import ForecastRepository, ModelEvaluationRepository
from app.forecasts.schemas import (
    BacktestResponse,
    ForecastAccuracyResponse,
    ForecastDay,
    ForecastDayItem,
    ForecastPointSchema,
    ForecastRunListResponse,
    ForecastRunSchema,
    GenerateForecastResponse,
    ItemChampionSchema,
    LatestForecastResponse,
    ModelEvaluationRunResponse,
    ModelEvaluationSchema,
    ModelSelectionSchema,
    PerItemEvaluationResponse,
)
from app.forecasts.service import ForecastService
from app.forecasts.tournament import ModelTournamentService, PerItemResult, TournamentResult
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
            ForecastDayItem(
                item_name=f.item_name,
                predicted_quantity=f.predicted_quantity,
                model_name=f.model_name,
            )
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


@router.get(
    "/locations/{location_id}/forecast-backtest",
    response_model=BacktestResponse,
)
async def forecast_backtest(
    location_id: UUID,
    user: CurrentUser,
    service: ForecastServiceDep,
    window_days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> BacktestResponse:
    result = await service.backtest(user=user, location_id=location_id, window_days=window_days)
    metrics = result.metrics
    return BacktestResponse(
        as_of=result.as_of,
        start_date=result.start_date,
        end_date=result.end_date,
        window_days=result.window_days,
        evaluated_observations=metrics.evaluated_observations,
        wape=metrics.wape,
        mae=metrics.mae,
        bias=metrics.bias,
    )


def get_tournament_service(session: SessionDep) -> ModelTournamentService:
    locations = LocationService(LocationRepository(session), RestaurantRepository(session))
    return ModelTournamentService(
        ModelEvaluationRepository(session), SalesRepository(session), locations
    )


TournamentServiceDep = Annotated[ModelTournamentService, Depends(get_tournament_service)]


def _tournament_response(result: TournamentResult) -> ModelEvaluationRunResponse:
    selection = result.selection
    models = [
        _model_schema(
            evaluation,
            is_baseline=evaluation.model_name == selection.baseline_model,
            is_selected=evaluation.model_name == selection.selected_model,
        )
        for evaluation in result.evaluations
    ]
    return ModelEvaluationRunResponse(
        id=result.run_id,
        location_id=result.location_id,
        horizon_days=result.config.horizon_days,
        min_training_days=result.config.min_training_days,
        window_step_days=result.config.step_days,
        window_count=max((len(e.windows) for e in result.evaluations), default=0),
        generated_at=result.generated_at,
        models=models,
        selection=_selection_schema(
            selection.baseline_model,
            selection.challenger_model,
            selection.selected_model,
            selection.relative_wape_improvement,
            selection.window_win_rate,
            selection.reason.value,
        ),
    )


def _run_response(run: ModelEvaluationRun) -> ModelEvaluationRunResponse:
    models = [
        ModelEvaluationSchema(
            model_name=result.model_name,
            is_baseline=result.is_baseline,
            is_selected=result.is_selected,
            evaluated_observations=result.evaluated_observations,
            wape=result.wape,
            mae=result.mae,
            rmse=result.rmse,
            bias=result.bias,
            bias_pct=result.bias_pct,
            mase=result.mase,
        )
        for result in run.evaluations
    ]
    return ModelEvaluationRunResponse(
        id=run.id,
        location_id=run.location_id,
        horizon_days=run.horizon_days,
        min_training_days=run.min_training_days,
        window_step_days=run.window_step_days,
        window_count=run.window_count,
        generated_at=run.generated_at,
        models=models,
        selection=_selection_schema(
            run.baseline_model,
            run.challenger_model,
            run.selected_model,
            run.relative_wape_improvement,
            run.window_win_rate,
            run.selection_reason,
        ),
    )


def _selection_schema(
    baseline: str,
    challenger: str | None,
    selected: str,
    relative_wape_improvement: object,
    window_win_rate: object,
    reason: str,
) -> ModelSelectionSchema:
    return ModelSelectionSchema(
        baseline_model=baseline,
        challenger_model=challenger,
        selected_model=selected,
        relative_wape_improvement=relative_wape_improvement,  # type: ignore[arg-type]
        window_win_rate=window_win_rate,  # type: ignore[arg-type]
        reason=reason,
    )


def _model_schema(
    evaluation: object,
    *,
    is_baseline: bool,
    is_selected: bool,
) -> ModelEvaluationSchema:
    # evaluation is a backtesting.ModelEvaluation; typed as object to avoid the
    # import cycle noise — attribute access is stable.
    agg = evaluation.aggregate  # type: ignore[attr-defined]
    return ModelEvaluationSchema(
        model_name=evaluation.model_name,  # type: ignore[attr-defined]
        is_baseline=is_baseline,
        is_selected=is_selected,
        evaluated_observations=agg.evaluated_observations,
        wape=agg.wape,
        mae=agg.mae,
        rmse=agg.rmse,
        bias=agg.bias,
        bias_pct=agg.bias_pct,
        mase=agg.mase,
    )


def _per_item_response(result: PerItemResult) -> PerItemEvaluationResponse:
    return PerItemEvaluationResponse(
        location_id=result.location_id,
        horizon_days=result.config.horizon_days,
        global_champion=result.global_champion,
        items=[
            ItemChampionSchema(
                item_name=champ.item_name,
                selected_model=champ.selection.selected_model,
                is_override=champ.selection.selected_model != result.global_champion,
                reason=champ.selection.reason.value,
                models=[
                    _model_schema(
                        evaluation,
                        is_baseline=evaluation.model_name == champ.selection.baseline_model,
                        is_selected=evaluation.model_name == champ.selection.selected_model,
                    )
                    for evaluation in champ.evaluations
                ],
            )
            for champ in result.items
        ],
    )


@router.post(
    "/locations/{location_id}/model-evaluations",
    status_code=status.HTTP_201_CREATED,
    response_model=ModelEvaluationRunResponse,
)
async def run_model_evaluation(
    location_id: UUID,
    user: CurrentUser,
    service: TournamentServiceDep,
) -> ModelEvaluationRunResponse:
    result = await service.evaluate(user=user, location_id=location_id)
    return _tournament_response(result)


@router.get(
    "/locations/{location_id}/model-evaluations/latest",
    response_model=ModelEvaluationRunResponse,
)
async def latest_model_evaluation(
    location_id: UUID,
    user: CurrentUser,
    service: TournamentServiceDep,
) -> ModelEvaluationRunResponse:
    run = await service.get_latest(user, location_id)
    return _run_response(run)


@router.get(
    "/locations/{location_id}/model-evaluations/by-item",
    response_model=PerItemEvaluationResponse,
)
async def model_evaluation_by_item(
    location_id: UUID,
    user: CurrentUser,
    service: TournamentServiceDep,
) -> PerItemEvaluationResponse:
    result = await service.evaluate_per_item(user=user, location_id=location_id)
    return _per_item_response(result)
