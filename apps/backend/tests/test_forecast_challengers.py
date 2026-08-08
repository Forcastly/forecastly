from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.algorithms.ewma_weekday import EwmaWeekdayModel
from app.forecasts.algorithms.level_adjusted_seasonal_naive import (
    LevelAdjustedSeasonalNaiveV2Model,
    level_ratio,
)
from app.forecasts.algorithms.seasonal_average import SeasonalAverageModel

MIN = Decimal("0.85")
MAX = Decimal("1.15")


def _series(start: date, quantities: list[int]) -> list[HistoricalObservation]:
    return [HistoricalObservation(start + timedelta(days=i), q) for i, q in enumerate(quantities)]


# --- Seasonal Average ------------------------------------------------------


def test_seasonal_average_means_recent_weekdays() -> None:
    start = date(2026, 1, 5)  # Monday
    # Five Mondays: 10, 20, 30, 40, 50 (+ filler days between).
    quantities: list[int] = []
    for monday in [10, 20, 30, 40, 50]:
        quantities.extend([monday, 0, 0, 0, 0, 0, 0])
    history = _series(start, quantities)
    origin = start + timedelta(days=34)  # last day present

    points = SeasonalAverageModel(weeks=4).predict(history, origin + timedelta(1), 7)
    monday = next(p for p in points if p.forecast_date.weekday() == 0)

    # Mean of the last 4 Mondays: (50 + 40 + 30 + 20) / 4 = 35.
    assert monday.predicted_quantity == Decimal("35.0000")


def test_seasonal_average_lower_variance_than_single_lag() -> None:
    # With noisy same-weekday values, the 4-week mean should sit between extremes.
    start = date(2026, 1, 5)
    quantities = []
    for monday in [10, 90, 10, 90]:
        quantities.extend([monday, 5, 5, 5, 5, 5, 5])
    history = _series(start, quantities)
    origin = start + timedelta(days=27)

    points = SeasonalAverageModel(weeks=4).predict(history, origin + timedelta(1), 7)
    monday = next(p for p in points if p.forecast_date.weekday() == 0)

    assert monday.predicted_quantity == Decimal("50.0000")  # (90+10+90+10)/4


# --- EWMA weekday ----------------------------------------------------------


def test_ewma_weights_recent_weekday_more() -> None:
    start = date(2026, 1, 5)
    quantities = []
    for monday in [10, 20, 40]:  # oldest -> newest
        quantities.extend([monday, 0, 0, 0, 0, 0, 0])
    history = _series(start, quantities)
    origin = start + timedelta(days=20)

    points = EwmaWeekdayModel(alpha=Decimal("0.5")).predict(history, origin + timedelta(1), 7)
    monday = next(p for p in points if p.forecast_date.weekday() == 0)

    # weights 1, .5, .25 on 40, 20, 10 -> (40 + 10 + 2.5) / 1.75 = 30.
    assert monday.predicted_quantity == Decimal("30.0000")


# --- Level-Adjusted v2 (shrinkage + gate) ----------------------------------


def _two_week(origin: date, recent: int, previous: int) -> dict[date, int]:
    by_date = {origin - timedelta(days=i): recent for i in range(7)}
    by_date |= {origin - timedelta(days=i): previous for i in range(7, 14)}
    return by_date


def test_v2_shrinks_toward_one() -> None:
    origin = date(2026, 1, 20)
    ratio = level_ratio(
        _two_week(origin, 120, 100),
        origin,
        recent_days=7,
        previous_days=7,
        min_ratio=MIN,
        max_ratio=MAX,
        shrinkage=Decimal("0.5"),
        min_rel_change=Decimal("0.05"),
    )
    # raw 1.20 -> 1 + 0.5*(0.20) = 1.10 (vs v1's 1.15 clamp).
    assert ratio == Decimal("1.10")


def test_v2_gates_small_moves() -> None:
    origin = date(2026, 1, 20)
    ratio = level_ratio(
        _two_week(origin, 103, 100),
        origin,
        recent_days=7,
        previous_days=7,
        min_ratio=MIN,
        max_ratio=MAX,
        shrinkage=Decimal("0.5"),
        min_rel_change=Decimal("0.05"),
    )
    assert ratio == Decimal("1")  # 3% move is below the 5% gate


def test_v2_model_uses_shrunk_ratio() -> None:
    origin = date(2026, 1, 20)  # Tuesday; O+1 is Wednesday
    by_date = _two_week(origin, 120, 100)  # recent week 120, previous week 100
    history = [HistoricalObservation(d, q) for d, q in sorted(by_date.items())]

    points = LevelAdjustedSeasonalNaiveV2Model().predict(history, origin + timedelta(1), 1)

    # seasonal reference (last Wed = 120) * shrunk ratio (1 + 0.5*0.2 = 1.10).
    assert points[0].predicted_quantity == Decimal("132.0000")
