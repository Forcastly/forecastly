"""Seasonal Naive model — the baseline/champion.

``forecast[t] = actual[t - seasonal_period]`` within one seasonal period, and the
last complete week repeated for longer horizons. This is the safe fallback the
tournament measures challengers against. Insufficient/absent history yields no
point for that day rather than an invented value.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.algorithms.base import (
    SEASONAL_PERIOD_DAYS,
    ForecastPoint,
    HistoricalObservation,
    quantize,
    seasonal_reference,
)


class SeasonalNaiveModel:
    name = "seasonal_naive"

    def __init__(self, seasonal_period_days: int = SEASONAL_PERIOD_DAYS) -> None:
        self.seasonal_period_days = seasonal_period_days

    def params(self) -> dict[str, object]:
        return {"seasonal_period_days": self.seasonal_period_days}

    def predict(
        self,
        history: Sequence[HistoricalObservation],
        forecast_start: date,
        horizon_days: int,
    ) -> list[ForecastPoint]:
        by_date = {obs.business_date: obs.quantity for obs in history}
        origin = forecast_start - timedelta(days=1)

        points: list[ForecastPoint] = []
        for offset in range(horizon_days):
            forecast_date = forecast_start + timedelta(days=offset)
            reference = seasonal_reference(
                by_date, forecast_date, origin, self.seasonal_period_days
            )
            if reference is None:
                continue
            points.append(ForecastPoint(forecast_date, quantize(Decimal(reference))))
        return points
