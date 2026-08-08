from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.engine import ForecastEngine, HistoricalObservation

engine = ForecastEngine()
REF = date(2026, 8, 3)  # arbitrary reference day
START = REF + timedelta(days=1)
SAME_WEEKDAY = REF + timedelta(days=7)  # a horizon date sharing REF's weekday


def _obs(offset_weeks: int, quantity: int) -> HistoricalObservation:
    return HistoricalObservation(REF - timedelta(days=7 * offset_weeks), quantity)


def _at(points: list, target: date) -> Decimal:
    return next(p.predicted_quantity for p in points if p.forecast_date == target)


def test_four_matching_weekdays_average() -> None:
    history = [_obs(0, 16), _obs(1, 14), _obs(2, 12), _obs(3, 10)]
    points = engine.generate(history, START, 7)
    assert _at(points, SAME_WEEKDAY) == Decimal("13.0000")


def test_uses_only_most_recent_four_matching() -> None:
    history = [_obs(k, 100) for k in range(1, 5)] + [_obs(0, 10)]  # 5 total, newest=10
    points = engine.generate(history, START, 7)
    # newest four are offsets 0..3 -> (10 + 100 + 100 + 100) / 4
    assert _at(points, SAME_WEEKDAY) == Decimal("77.5000")


def test_fewer_than_four_matching_uses_available() -> None:
    history = [_obs(0, 20), _obs(1, 10)]
    points = engine.generate(history, START, 7)
    assert _at(points, SAME_WEEKDAY) == Decimal("15.0000")


def test_no_matching_weekday_falls_back_to_recent() -> None:
    history = [_obs(0, 30), _obs(1, 20), _obs(2, 10)]  # all one weekday
    points = engine.generate(history, START, 7)
    # START is a different weekday -> fallback to recent average of all 3
    assert _at(points, START) == Decimal("20.0000")


def test_zero_observations_count() -> None:
    history = [_obs(0, 5), _obs(1, 3), _obs(2, 4), _obs(3, 0)]
    points = engine.generate(history, START, 7)
    assert _at(points, SAME_WEEKDAY) == Decimal("3.0000")


def test_no_history_yields_no_points() -> None:
    assert engine.generate([], START, 7) == []


def test_horizon_dates_are_contiguous() -> None:
    points = engine.generate([_obs(0, 10)], START, 7)
    assert [p.forecast_date for p in points] == [
        START + timedelta(days=offset) for offset in range(7)
    ]
    assert all(p.predicted_quantity >= 0 for p in points)
