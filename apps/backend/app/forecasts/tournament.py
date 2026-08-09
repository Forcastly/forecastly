"""Model tournament orchestration.

Loads a location's sales history once, backtests both candidate models over the
same rolling-origin windows, selects a champion, and persists the run (aggregate
+ per-window results + selection reason) for lineage. Production forecasting is
unaffected — this establishes the evaluation/selection foundation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.backtesting import (
    BacktestConfig,
    ModelEvaluation,
    RollingOriginBacktester,
)
from app.forecasts.champions import BASELINE_MODEL, candidate_models
from app.forecasts.exceptions import (
    InsufficientForecastHistoryError,
    ModelEvaluationNotFoundError,
)
from app.forecasts.metrics import EvaluationMetrics
from app.forecasts.models import (
    ModelEvaluationResult,
    ModelEvaluationRun,
    ModelEvaluationWindow,
)
from app.forecasts.repository import ModelEvaluationRepository
from app.forecasts.selection import ModelSelection, select_champion
from app.locations.service import LocationService
from app.sales.repository import SalesRepository
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TournamentResult:
    run_id: UUID
    location_id: UUID
    generated_at: datetime
    config: BacktestConfig
    evaluations: list[ModelEvaluation]
    selection: ModelSelection


@dataclass(frozen=True, slots=True)
class ItemChampion:
    item_name: str
    evaluations: list[ModelEvaluation]
    selection: ModelSelection


@dataclass(frozen=True, slots=True)
class PerItemResult:
    location_id: UUID
    config: BacktestConfig
    global_champion: str
    items: list[ItemChampion]


class ModelTournamentService:
    def __init__(
        self,
        repository: ModelEvaluationRepository,
        sales: SalesRepository,
        locations: LocationService,
        config: BacktestConfig | None = None,
    ) -> None:
        self.repository = repository
        self.sales = sales
        self.locations = locations
        self.config = config or BacktestConfig()
        self.backtester = RollingOriginBacktester(self.config)

    @property
    def session(self) -> AsyncSession:
        return self.repository.session

    async def evaluate(self, *, user: User, location_id: UUID) -> TournamentResult:
        location = await self.locations.get(user, location_id)  # 404 if inaccessible
        observations = await self.sales.list_observations(location.id)
        if not observations:
            raise InsufficientForecastHistoryError()

        history_by_item: dict[str, list[HistoricalObservation]] = defaultdict(list)
        for obs in observations:
            history_by_item[obs.item_name_normalized].append(
                HistoricalObservation(obs.business_date, obs.quantity)
            )

        evaluations = self.backtester.evaluate(candidate_models(), history_by_item)
        selection = select_champion(evaluations, BASELINE_MODEL)

        generated_at = _now()
        run = self._build_run(location.id, generated_at, evaluations, selection)
        await self.repository.add(run)
        await self.session.commit()

        return TournamentResult(
            run_id=run.id,
            location_id=location.id,
            generated_at=generated_at,
            config=self.config,
            evaluations=evaluations,
            selection=selection,
        )

    async def evaluate_per_item(self, *, user: User, location_id: UUID) -> PerItemResult:
        """Hybrid per-item selection (on-demand; not persisted).

        The pooled global champion is the default for every item; a per-item model
        overrides it only when it clears the full promotion gate (relative WAPE
        margin + window consistency + no bias regression) against the global
        champion on that item. This captures real per-item wins while avoiding
        overfitting to thin per-item margins.
        """
        location = await self.locations.get(user, location_id)
        observations = await self.sales.list_observations(location.id)
        if not observations:
            raise InsufficientForecastHistoryError()

        history_by_item: dict[str, list[HistoricalObservation]] = defaultdict(list)
        display_name: dict[str, str] = {}
        for obs in observations:
            history_by_item[obs.item_name_normalized].append(
                HistoricalObservation(obs.business_date, obs.quantity)
            )
            display_name[obs.item_name_normalized] = obs.item_name

        # Global champion from the pooled tournament = per-item default/fallback.
        pooled = self.backtester.evaluate(candidate_models(), history_by_item)
        global_champion = select_champion(pooled, BASELINE_MODEL).selected_model

        per_item = self.backtester.evaluate_per_item(candidate_models(), history_by_item)
        items = [
            ItemChampion(
                item_name=display_name[normalized],
                evaluations=evaluations,
                # Baseline = global champion: override only on a clear per-item win.
                selection=select_champion(evaluations, global_champion),
            )
            for normalized, evaluations in per_item.items()
        ]
        items.sort(key=lambda champ: champ.item_name)
        return PerItemResult(
            location_id=location.id,
            config=self.config,
            global_champion=global_champion,
            items=items,
        )

    async def get_latest(self, user: User, location_id: UUID) -> ModelEvaluationRun:
        location = await self.locations.get(user, location_id)
        run = await self.repository.latest(location.id)
        if run is None:
            raise ModelEvaluationNotFoundError()
        return run

    def _build_run(
        self,
        location_id: UUID,
        generated_at: datetime,
        evaluations: list[ModelEvaluation],
        selection: ModelSelection,
    ) -> ModelEvaluationRun:
        window_count = max((len(e.windows) for e in evaluations), default=0)
        results = [
            ModelEvaluationResult(
                model_name=evaluation.model_name,
                model_params=evaluation.params,
                is_baseline=evaluation.model_name == selection.baseline_model,
                is_selected=evaluation.model_name == selection.selected_model,
                windows=[
                    ModelEvaluationWindow(
                        forecast_origin=result.window.forecast_origin,
                        train_start=result.window.train_start,
                        train_end=result.window.train_end,
                        forecast_start=result.window.forecast_start,
                        forecast_end=result.window.forecast_end,
                        horizon_days=result.window.horizon_days,
                        **_metric_columns(result.metrics),
                    )
                    for result in evaluation.windows
                ],
                **_metric_columns(evaluation.aggregate),
            )
            for evaluation in evaluations
        ]
        return ModelEvaluationRun(
            location_id=location_id,
            horizon_days=self.config.horizon_days,
            min_training_days=self.config.min_training_days,
            window_step_days=self.config.step_days,
            window_count=window_count,
            baseline_model=selection.baseline_model,
            challenger_model=selection.challenger_model,
            selected_model=selection.selected_model,
            selection_reason=selection.reason.value,
            relative_wape_improvement=selection.relative_wape_improvement,
            window_win_rate=selection.window_win_rate,
            generated_at=generated_at,
            evaluations=results,
        )


def _metric_columns(metrics: EvaluationMetrics) -> dict[str, object]:
    return {
        "evaluated_observations": metrics.evaluated_observations,
        "wape": metrics.wape,
        "mae": metrics.mae,
        "rmse": metrics.rmse,
        "bias": metrics.bias,
        "bias_pct": metrics.bias_pct,
        "mase": metrics.mase,
    }
