from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.algorithms.seasonal_naive import SeasonalNaiveModel
from app.forecasts.backtesting import BacktestConfig, RollingOriginBacktester

START = date(2026, 1, 5)  # Monday


def _make(days: int, fn: Callable[[date], int]) -> list[HistoricalObservation]:
    return [
        HistoricalObservation(START + timedelta(days=i), fn(START + timedelta(days=i)))
        for i in range(days)
    ]


def _weekly(day: date) -> int:
    return 10 + day.weekday()  # deterministic weekly seasonality


def test_build_windows_origins_and_cutoffs() -> None:
    max_date = START + timedelta(days=59)
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=3, step_days=7)

    windows = RollingOriginBacktester(cfg).build_windows(START, max_date)

    assert len(windows) == 3
    newest = windows[-1]
    assert newest.forecast_origin == max_date - timedelta(days=7)
    assert newest.train_end == newest.forecast_origin
    assert newest.forecast_start == newest.forecast_origin + timedelta(days=1)
    assert newest.forecast_end == newest.forecast_origin + timedelta(days=7)
    # Oldest first, stepping back by 7 days.
    assert windows[0].forecast_origin == max_date - timedelta(days=7 + 14)


def test_build_windows_limited_by_history() -> None:
    max_date = START + timedelta(days=40)
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=8, step_days=7)

    windows = RollingOriginBacktester(cfg).build_windows(START, max_date)

    assert len(windows) == 3  # origins at +33, +26, +19; +12 fails min_training
    assert all((w.forecast_origin - START).days >= 14 for w in windows)


def test_evaluate_counts_and_seasonal_correctness() -> None:
    history = {"burger": _make(60, _weekly)}
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=3, step_days=7)

    evaluation = RollingOriginBacktester(cfg).evaluate([SeasonalNaiveModel()], history)[0]

    assert evaluation.model_name == "seasonal_naive"
    assert evaluation.aggregate.evaluated_observations == 21  # 3 windows x 7 days
    assert evaluation.aggregate.wape == Decimal("0")  # weekly pattern -> perfect
    assert len(evaluation.windows) == 3
    assert all(w.metrics.evaluated_observations == 7 for w in evaluation.windows)
    assert set(evaluation.horizon_slices) == {1, 2, 3, 4, 5, 6, 7}
    assert len(evaluation.weekday_slices) == 7


def test_earlier_window_unaffected_by_later_data() -> None:
    base = _make(60, _weekly)
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=3, step_days=7)
    backtester = RollingOriginBacktester(cfg)

    before = backtester.evaluate([SeasonalNaiveModel()], {"burger": base})[0]
    earliest = before.windows[0]
    # Mutate an actual strictly after the earliest window's forecast period.
    mutate_date = earliest.window.forecast_end + timedelta(days=3)
    mutated = [
        HistoricalObservation(o.business_date, o.quantity + 500)
        if o.business_date == mutate_date
        else o
        for o in base
    ]
    after = backtester.evaluate([SeasonalNaiveModel()], {"burger": mutated})[0]

    # The earliest window neither trained on nor forecast that date -> identical.
    assert after.windows[0].metrics == before.windows[0].metrics
    # A later window did see it, so the aggregate changed (sanity check).
    assert after.aggregate != before.aggregate


def test_adding_a_model_needs_no_backtester_change() -> None:
    # Two models evaluated over identical windows via the same generic loop.
    from app.forecasts.algorithms.level_adjusted_seasonal_naive import (
        LevelAdjustedSeasonalNaiveModel,
    )

    history = {"burger": _make(60, _weekly)}
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=2, step_days=7)

    results = RollingOriginBacktester(cfg).evaluate(
        [SeasonalNaiveModel(), LevelAdjustedSeasonalNaiveModel()], history
    )

    assert [r.model_name for r in results] == [
        "seasonal_naive",
        "level_adjusted_seasonal_naive",
    ]
    assert all(len(r.windows) == 2 for r in results)
