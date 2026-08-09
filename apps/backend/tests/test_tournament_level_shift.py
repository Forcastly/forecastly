"""End-to-end: on volatile same-weekday demand, a lower-variance averaging
challenger beats single-lag Seasonal Naive on every window and is promoted."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms import (
    EwmaWeekdayModel,
    LevelAdjustedSeasonalNaiveV2Model,
    SeasonalAverageModel,
    SeasonalNaiveModel,
)
from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.backtesting import BacktestConfig, RollingOriginBacktester
from app.forecasts.selection import SelectionReason, select_champion

START = date(2026, 1, 5)  # Monday
BASELINE = "seasonal_naive"


def _oscillating_history() -> list[HistoricalObservation]:
    # Same-weekday value alternates ±40 week to week around a weekly shape. Over a
    # one-week horizon the single lag is always ~80 off (opposite parity), while a
    # 4-week average cancels the swing to ~40 off — so the averaging challenger
    # wins every window decisively. 84 days.
    def quantity(i: int) -> int:
        base = 100 + (i % 7) * 10
        return base + (40 if (i // 7) % 2 == 0 else -40)

    return [HistoricalObservation(START + timedelta(days=i), quantity(i)) for i in range(84)]


def test_averaging_challenger_promoted_over_single_lag() -> None:
    history = {"burger": _oscillating_history()}
    cfg = BacktestConfig(horizon_days=7, min_training_days=28, num_windows=6, step_days=7)
    models = [
        SeasonalNaiveModel(),
        SeasonalAverageModel(),
        EwmaWeekdayModel(),
        LevelAdjustedSeasonalNaiveV2Model(),
    ]

    evaluations = RollingOriginBacktester(cfg).evaluate(models, history)
    by_name = {e.model_name: e for e in evaluations}
    selection = select_champion(evaluations, BASELINE)

    baseline_wape = by_name[BASELINE].aggregate.wape
    challenger_wapes = [
        w for e in evaluations if e.model_name != BASELINE and (w := e.aggregate.wape) is not None
    ]
    assert challenger_wapes and baseline_wape is not None
    assert min(challenger_wapes) < baseline_wape  # a challenger beats the baseline

    assert selection.selected_model == "seasonal_average"  # lowest-WAPE challenger
    assert selection.reason is SelectionReason.CHALLENGER_PROMOTED
    assert selection.window_win_rate == Decimal("1")  # wins every window
