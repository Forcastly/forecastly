"""Model roster and champion selection shared by the tournament and production.

`select_item_models` runs the hybrid tournament (pooled global champion, then a
per-item override only on a clear win) and returns the concrete model instance to
use for each item. Production forecasting calls this to drive the real forecast;
the tournament API calls the same roster so evaluation and production never drift.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.forecasts.algorithms import (
    EwmaWeekdayModel,
    ForecastModel,
    HoltWintersModel,
    LevelAdjustedSeasonalNaiveV2Model,
    SeasonalAverageModel,
    SeasonalNaiveModel,
)
from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.backtesting import BacktestConfig, RollingOriginBacktester
from app.forecasts.selection import select_champion

BASELINE_MODEL = SeasonalNaiveModel.name
# Version tag stored on production forecast runs that use hybrid champion selection.
PRODUCTION_MODEL_VERSION = "champion_hybrid_v1"


def candidate_models() -> list[ForecastModel]:
    """The tournament roster. Baseline first, then challengers. Adding a model
    here enters it in both evaluation and production selection."""
    return [
        SeasonalNaiveModel(),
        SeasonalAverageModel(),
        EwmaWeekdayModel(),
        LevelAdjustedSeasonalNaiveV2Model(),
        HoltWintersModel(),
    ]


def select_item_models(
    history_by_item: Mapping[str, Sequence[HistoricalObservation]],
    config: BacktestConfig | None = None,
) -> tuple[str, dict[str, ForecastModel]]:
    """Return ``(global_champion_name, {item: model})`` via the hybrid tournament.

    The global champion is the pooled winner; each item keeps it unless another
    model clears the promotion gate for that item. Callers apply the returned
    models with their own horizon. If history is too thin to build backtest
    windows the selection degrades to the baseline for every item — callers
    should keep their own fallback for items a model cannot forecast.
    """
    models = candidate_models()
    by_name = {model.name: model for model in models}
    backtester = RollingOriginBacktester(config or BacktestConfig())

    pooled = backtester.evaluate(models, history_by_item)
    global_champion = select_champion(pooled, BASELINE_MODEL).selected_model

    # No backtest windows means history is too thin to choose a champion at all;
    # signal "no selection" so the caller uses its own fallback for every item.
    if max((len(e.windows) for e in pooled), default=0) == 0:
        return global_champion, {}

    per_item = backtester.evaluate_per_item(models, history_by_item)
    chosen = {
        item: by_name[select_champion(evaluations, global_champion).selected_model]
        for item, evaluations in per_item.items()
    }
    return global_champion, chosen
