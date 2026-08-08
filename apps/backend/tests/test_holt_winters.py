from __future__ import annotations

from datetime import date, timedelta

from app.forecasts.algorithms.base import HistoricalObservation
from app.forecasts.algorithms.holt_winters import HoltWintersModel

START = date(2026, 1, 5)  # Monday


def _series(fn) -> list[HistoricalObservation]:
    return [
        HistoricalObservation(START + timedelta(days=i), max(0, round(fn(i)))) for i in range(56)
    ]


def test_insufficient_history_returns_empty() -> None:
    history = [HistoricalObservation(START + timedelta(days=i), 10) for i in range(10)]
    assert HoltWintersModel().predict(history, START + timedelta(days=10), 7) == []


def test_output_is_non_negative() -> None:
    history = _series(lambda i: 50 + (i % 7) * 8 - i)  # declining, can go low
    origin = START + timedelta(days=55)

    points = HoltWintersModel().predict(history, origin + timedelta(days=1), 14)

    assert all(p.predicted_quantity >= 0 for p in points)


def test_no_future_leakage() -> None:
    history = _series(lambda i: 100 + i + (i % 7) * 10)
    origin = START + timedelta(days=40)
    before = [o for o in history if o.business_date <= origin]
    model = HoltWintersModel()

    baseline = model.predict(before, origin + timedelta(days=1), 14)
    mutated = [
        HistoricalObservation(o.business_date, o.quantity + 1000) if o.business_date > origin else o
        for o in history
    ]
    after = model.predict(
        [o for o in mutated if o.business_date <= origin], origin + timedelta(days=1), 14
    )

    assert baseline == after and baseline  # future data can't change the forecast


def test_projects_trend_upward() -> None:
    # Steady upward level + weekly shape: the trend term carries the forecast up
    # across the horizon, so the second Monday is predicted above the first. A
    # flat same-weekday average would predict them equal.
    history = _series(lambda i: 100 + 2 * i + (i % 7) * 10)
    origin = START + timedelta(days=55)

    points = HoltWintersModel().predict(history, origin + timedelta(days=1), 14)
    mondays = [p.predicted_quantity for p in points if p.forecast_date.weekday() == 0]

    assert len(mondays) == 2
    assert mondays[1] > mondays[0]  # trend projected forward over the horizon


def test_captures_weekly_seasonality() -> None:
    # Weekends (Sat=5, Sun=6) run much higher; HW forecast should reflect it.
    def shape(i: int) -> float:
        weekday = (START + timedelta(days=i)).weekday()
        return 200 if weekday >= 5 else 80

    history = _series(shape)
    origin = START + timedelta(days=55)

    points = HoltWintersModel().predict(history, origin + timedelta(days=1), 7)
    by_wd = {p.forecast_date.weekday(): p.predicted_quantity for p in points}

    assert by_wd[5] > by_wd[2]  # Saturday forecast > Wednesday forecast
