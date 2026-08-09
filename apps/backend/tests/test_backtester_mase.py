from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.algorithms.seasonal_naive import SeasonalNaiveModel
from app.forecasts.backtesting import BacktestConfig, RollingOriginBacktester
from app.forecasts.metrics import seasonal_scale

START = date(2026, 1, 5)  # Monday


def test_seasonal_scale_is_in_sample_seasonal_naive_mae() -> None:
    # x_t - x_{t-7} = +7 each week (values rise by 1/day, weekly diff constant).
    by_date = {START + timedelta(days=i): 10 + i for i in range(21)}
    assert seasonal_scale(by_date, 7) == Decimal("7")


def test_seasonal_scale_none_when_flat() -> None:
    by_date = {START + timedelta(days=i): 50 for i in range(21)}
    assert seasonal_scale(by_date, 7) is None  # zero scale -> undefined MASE


def test_backtester_reports_mase_none_for_perfect_seasonal() -> None:
    # Perfect weekly pattern: in-sample seasonal-naive error is 0, so the MASE
    # scale is undefined -> MASE is None (never a divide-by-zero).
    history = {
        "burger": [
            HistoricalObservation(
                START + timedelta(days=i), 10 + (START + timedelta(days=i)).weekday()
            )
            for i in range(60)
        ]
    }
    cfg = BacktestConfig(horizon_days=7, min_training_days=14, num_windows=3, step_days=7)

    evaluation = RollingOriginBacktester(cfg).evaluate([SeasonalNaiveModel()], history)[0]

    assert evaluation.aggregate.mase is None


def test_backtester_reports_mase_one_for_seasonal_naive_on_oscillating() -> None:
    # Same-weekday values alternate ±40 each week: seasonal naive's holdout error
    # equals its in-sample seasonal-naive error -> MASE == 1.
    def quantity(i: int) -> int:
        base = 50 + (i % 7) * 8
        return base + (40 if (i // 7) % 2 == 0 else -40)

    history = {
        "burger": [HistoricalObservation(START + timedelta(days=i), quantity(i)) for i in range(84)]
    }
    cfg = BacktestConfig(horizon_days=7, min_training_days=28, num_windows=4, step_days=7)

    evaluation = RollingOriginBacktester(cfg).evaluate([SeasonalNaiveModel()], history)[0]

    assert evaluation.aggregate.mase == Decimal("1")
