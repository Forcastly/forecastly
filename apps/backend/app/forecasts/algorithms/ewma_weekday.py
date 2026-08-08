"""EWMA-weighted same-weekday model.

``forecast[t] = Σ wᵢ·x_{t-7(i+1)} / Σ wᵢ`` with geometric weights
``wᵢ = (1-α)^i`` over the most recent same-weekday observations. α is a
bias/variance knob: α→1 approaches Seasonal Naive (only the latest lag), α→0
approaches a flat Seasonal Average. It tracks a drifting level faster than a flat
mean while keeping variance low.
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

DEFAULT_ALPHA = Decimal("0.5")
DEFAULT_MAX_WEEKS = 8


class EwmaWeekdayModel:
    name = "ewma_weekday"

    def __init__(
        self,
        seasonal_period_days: int = SEASONAL_PERIOD_DAYS,
        alpha: Decimal = DEFAULT_ALPHA,
        max_weeks: int = DEFAULT_MAX_WEEKS,
    ) -> None:
        self.seasonal_period_days = seasonal_period_days
        self.alpha = alpha
        self.max_weeks = max_weeks

    def params(self) -> dict[str, object]:
        return {
            "seasonal_period_days": self.seasonal_period_days,
            "alpha": str(self.alpha),
            "max_weeks": self.max_weeks,
        }

    def predict(
        self,
        history: Sequence[HistoricalObservation],
        forecast_start: date,
        horizon_days: int,
    ) -> list[ForecastPoint]:
        by_date = {obs.business_date: obs.quantity for obs in history}
        origin = forecast_start - timedelta(days=1)
        decay = Decimal(1) - self.alpha

        points: list[ForecastPoint] = []
        for offset in range(horizon_days):
            forecast_date = forecast_start + timedelta(days=offset)
            values = same_weekday_history(
                by_date, forecast_date, origin, self.seasonal_period_days
            )[: self.max_weeks]
            if not values:
                continue
            weight = Decimal(1)
            weighted_sum = Decimal(0)
            weight_total = Decimal(0)
            for value in values:  # most recent first
                weighted_sum += weight * Decimal(value)
                weight_total += weight
                weight *= decay
            predicted = weighted_sum / weight_total if weight_total > 0 else Decimal(0)
            points.append(ForecastPoint(forecast_date, quantize(predicted)))
        return points
