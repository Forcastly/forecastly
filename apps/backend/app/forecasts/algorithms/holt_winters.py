"""Holt-Winters model — triple exponential smoothing.

Tracks three components, each an EWMA updated per day, using only data on/before
the forecast origin:

- level   L : current baseline demand
- trend   b : per-day slope of the level (damped over the horizon by phi)
- season  s : multiplicative weekly factors, indexed by weekday (gap-tolerant)

Forecast h days ahead:

    y_hat = (L + (phi + phi^2 + ... + phi^h) * b) * season[weekday]

The explicit trend term is the point: it projects a rising/falling level forward
instead of lagging it, which corrects the systematic under/over-forecast that
pure same-weekday averaging shows on trending demand.

Multiplicative seasonality is guarded with a small epsilon so zero-demand days
never cause division by zero; output is clamped non-negative. Needs at least two
full weekly seasons of history; otherwise it produces nothing and the tournament
falls back to another model. Parameters are fixed, sensible defaults (not fitted),
so the model stays deterministic and cheap.
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
)

DEFAULT_ALPHA = 0.3  # level smoothing
DEFAULT_BETA = 0.05  # trend smoothing
DEFAULT_GAMMA = 0.2  # seasonal smoothing
DEFAULT_PHI = 0.9  # trend damping
_EPSILON = 1e-6


class HoltWintersModel:
    name = "holt_winters"

    def __init__(
        self,
        *,
        seasonal_period_days: int = SEASONAL_PERIOD_DAYS,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA,
        phi: float = DEFAULT_PHI,
    ) -> None:
        self.seasonal_period_days = seasonal_period_days
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.phi = phi

    def params(self) -> dict[str, object]:
        return {
            "seasonal_period_days": self.seasonal_period_days,
            "alpha": str(self.alpha),
            "beta": str(self.beta),
            "gamma": str(self.gamma),
            "phi": str(self.phi),
        }

    def predict(
        self,
        history: Sequence[HistoricalObservation],
        forecast_start: date,
        horizon_days: int,
    ) -> list[ForecastPoint]:
        m = self.seasonal_period_days
        ordered = sorted(history, key=lambda obs: obs.business_date)
        if len(ordered) < 2 * m:
            return []  # need >= 2 seasons to initialize trend + seasonality

        values = [float(obs.quantity) for obs in ordered]
        weekdays = [obs.business_date.weekday() for obs in ordered]

        level = sum(values[:m]) / m
        second = sum(values[m : 2 * m]) / m
        trend = (second - level) / m
        if level < _EPSILON:
            return []  # near-zero baseline: multiplicative form is undefined

        # Initialize weekday seasonal factors from the first two seasons.
        seasonal: dict[int, float] = {}
        for weekday in set(weekdays[: 2 * m]):
            samples = [values[i] for i in range(2 * m) if weekdays[i] == weekday]
            seasonal[weekday] = max(sum(samples) / len(samples) / level, _EPSILON)

        # Recurse over the full history (data <= origin only).
        for value, weekday in zip(values, weekdays, strict=True):
            s = seasonal.get(weekday, 1.0)
            prev_level = level
            level = self.alpha * (value / s) + (1 - self.alpha) * (level + self.phi * trend)
            level = max(level, _EPSILON)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * self.phi * trend
            seasonal[weekday] = max(self.gamma * (value / level) + (1 - self.gamma) * s, _EPSILON)

        if not _finite(level) or not _finite(trend):
            return []

        points: list[ForecastPoint] = []
        damp_sum = 0.0
        phi_power = 1.0
        for offset in range(horizon_days):
            phi_power *= self.phi
            damp_sum += phi_power  # phi + phi^2 + ... + phi^(offset+1)
            forecast_date = forecast_start + timedelta(days=offset)
            factor = seasonal.get(forecast_date.weekday(), 1.0)
            predicted = (level + damp_sum * trend) * factor
            predicted = max(predicted, 0.0)  # demand is non-negative
            points.append(ForecastPoint(forecast_date, quantize(Decimal(str(predicted)))))
        return points


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
