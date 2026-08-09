from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.algorithms.level_adjusted_seasonal_naive import (
    LevelAdjustedSeasonalNaiveModel,
    level_ratio,
)
from app.forecasts.algorithms.seasonal_naive import SeasonalNaiveModel

MIN = Decimal("0.85")
MAX = Decimal("1.15")


def _series(start: date, quantities: list[int]) -> list[HistoricalObservation]:
    return [HistoricalObservation(start + timedelta(days=i), q) for i, q in enumerate(quantities)]


# --- Seasonal Naive --------------------------------------------------------


def test_seasonal_naive_weekly_lookup() -> None:
    start = date(2026, 1, 5)  # Monday
    history = _series(start, list(range(1, 22)))  # 21 distinct daily values
    origin = start + timedelta(days=20)
    by_date = {o.business_date: o.quantity for o in history}

    points = SeasonalNaiveModel().predict(history, origin + timedelta(days=1), 7)

    assert len(points) == 7
    for point in points:
        expected = Decimal(by_date[point.forecast_date - timedelta(days=7)])
        assert point.predicted_quantity == expected  # forecast[t] = actual[t-7]


def test_seasonal_naive_multi_week_repeats_last_complete_week() -> None:
    start = date(2026, 1, 5)
    history = _series(start, list(range(1, 22)))  # 3 weeks
    origin = start + timedelta(days=20)

    points = SeasonalNaiveModel().predict(history, origin + timedelta(days=1), 14)
    by_forecast = {p.forecast_date: p.predicted_quantity for p in points}
    by_date = {o.business_date: o.quantity for o in history}

    # Day +8 has no actual[t-7] on/before origin, so it repeats actual[t-14].
    day8 = origin + timedelta(days=8)
    assert by_forecast[day8] == Decimal(by_date[day8 - timedelta(days=14)])


def test_seasonal_naive_partial_history_forecasts_only_known_weekdays() -> None:
    start = date(2026, 1, 5)  # Mon, Tue, Wed
    history = _series(start, [10, 11, 12])
    origin = start + timedelta(days=2)  # Wed

    # Horizon Thu..Wed: only Mon/Tue/Wed have a same-weekday reference.
    points = SeasonalNaiveModel().predict(history, origin + timedelta(days=1), 7)

    assert {p.forecast_date for p in points} == {
        date(2026, 1, 12),  # Mon -> actual[Jan 5]
        date(2026, 1, 13),  # Tue -> actual[Jan 6]
        date(2026, 1, 14),  # Wed -> actual[Jan 7]
    }
    assert [p.predicted_quantity for p in points] == [
        Decimal("10.0000"),
        Decimal("11.0000"),
        Decimal("12.0000"),
    ]


def test_seasonal_naive_skips_days_without_reference() -> None:
    start = date(2026, 1, 5)  # Mon, Tue, Wed
    history = _series(start, [10, 11, 12])
    origin = start + timedelta(days=2)  # Wed

    # Horizon Thu, Fri, Sat — none share a weekday with the history.
    points = SeasonalNaiveModel().predict(history, origin + timedelta(days=1), 3)

    assert points == []  # nothing invented


def test_seasonal_naive_no_future_leakage() -> None:
    start = date(2026, 1, 5)
    history = _series(start, list(range(1, 29)))  # 28 days
    origin = start + timedelta(days=20)
    before = [o for o in history if o.business_date <= origin]
    model = SeasonalNaiveModel()

    baseline = model.predict(before, origin + timedelta(days=1), 14)
    # Mutate observations strictly after the origin (they are within the horizon).
    mutated = [
        HistoricalObservation(o.business_date, o.quantity + 1000) if o.business_date > origin else o
        for o in history
    ]
    before_mutated = [o for o in mutated if o.business_date <= origin]
    after = model.predict(before_mutated, origin + timedelta(days=1), 14)

    assert baseline == after and baseline  # predictions unchanged by future data


# --- Level ratio -----------------------------------------------------------


def _ratio(by_date: dict[date, int], origin: date) -> Decimal:
    return level_ratio(
        by_date, origin, recent_days=7, previous_days=7, min_ratio=MIN, max_ratio=MAX
    )


def _two_week_levels(origin: date, recent: int, previous: int) -> dict[date, int]:
    by_date = {origin - timedelta(days=i): recent for i in range(7)}  # O-6..O
    by_date |= {origin - timedelta(days=i): previous for i in range(7, 14)}  # O-13..O-7
    return by_date


def test_level_ratio_stable() -> None:
    origin = date(2026, 1, 20)
    assert _ratio(_two_week_levels(origin, 100, 100), origin) == Decimal("1")


def test_level_ratio_upward() -> None:
    origin = date(2026, 1, 20)
    assert _ratio(_two_week_levels(origin, 110, 100), origin) == Decimal("1.1")


def test_level_ratio_caps_high() -> None:
    origin = date(2026, 1, 20)
    assert _ratio(_two_week_levels(origin, 200, 100), origin) == MAX


def test_level_ratio_caps_low() -> None:
    origin = date(2026, 1, 20)
    assert _ratio(_two_week_levels(origin, 50, 100), origin) == MIN


def test_level_ratio_zero_previous() -> None:
    origin = date(2026, 1, 20)
    assert _ratio(_two_week_levels(origin, 100, 0), origin) == Decimal("1")


def test_level_ratio_insufficient_history() -> None:
    origin = date(2026, 1, 20)
    recent_only = {origin - timedelta(days=i): 100 for i in range(7)}
    assert _ratio(recent_only, origin) == Decimal("1")


# --- Level-Adjusted Seasonal Naive ----------------------------------------


def test_level_adjusted_scales_seasonal_value() -> None:
    origin = date(2026, 1, 20)
    # Previous week mean 100; recent week mean 110 with the O-6 day equal to 100.
    by_date = {origin - timedelta(days=i): 100 for i in range(7, 14)}
    recent = {origin - timedelta(days=6): 100}  # the seasonal reference for O+1
    recent |= {origin - timedelta(days=i): 100 for i in range(1, 6)}
    recent[origin] = 170  # pushes recent mean to (100*6 + 170)/7 = 110
    by_date |= recent
    history = [HistoricalObservation(d, q) for d, q in sorted(by_date.items())]

    points = LevelAdjustedSeasonalNaiveModel().predict(history, origin + timedelta(1), 1)

    assert points[0].forecast_date == origin + timedelta(days=1)
    assert points[0].predicted_quantity == Decimal("110.0000")  # 100 * 1.10


def test_level_adjusted_applies_upper_cap() -> None:
    origin = date(2026, 1, 20)
    by_date = _two_week_levels(origin, 200, 100)  # raw ratio 2.0 -> clamp 1.15
    by_date[origin - timedelta(days=6)] = 100  # seasonal reference for O+1
    history = [HistoricalObservation(d, q) for d, q in sorted(by_date.items())]

    points = LevelAdjustedSeasonalNaiveModel().predict(history, origin + timedelta(1), 1)

    assert points[0].predicted_quantity == Decimal("115.0000")  # 100 * 1.15


def test_level_adjusted_falls_back_to_seasonal_naive() -> None:
    origin = date(2026, 1, 20)
    recent_only = {origin - timedelta(days=i): 100 for i in range(7)}  # no previous week
    history = [HistoricalObservation(d, q) for d, q in sorted(recent_only.items())]

    points = LevelAdjustedSeasonalNaiveModel().predict(history, origin + timedelta(1), 1)

    assert points[0].predicted_quantity == Decimal("100.0000")  # ratio 1.0
