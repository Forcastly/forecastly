"""Seasonal Average model.

``forecast[t] = mean of the most recent K same-weekday observations``. Averaging K
lags cuts variance ~K-fold versus the single-lag Seasonal Naive baseline, which is
the main win on noisy but level-stable demand. Falls back to whatever same-weekday
history exists (no invention).
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
    same_weekday_history,
)

DEFAULT_WEEKS = 4


class SeasonalAverageModel:
    name = "seasonal_average"

    def __init__(
        self,
        seasonal_period_days: int = SEASONAL_PERIOD_DAYS,
        weeks: int = DEFAULT_WEEKS,
    ) -> None:
        self.seasonal_period_days = seasonal_period_days
        self.weeks = weeks

    def params(self) -> dict[str, object]:
        return {"seasonal_period_days": self.seasonal_period_days, "weeks": self.weeks}

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
            values = same_weekday_history(
                by_date, forecast_date, origin, self.seasonal_period_days
            )[: self.weeks]
            if not values:
                continue
            predicted = Decimal(sum(values)) / Decimal(len(values))
            points.append(ForecastPoint(forecast_date, quantize(predicted)))
        return points
