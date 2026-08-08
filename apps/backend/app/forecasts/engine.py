"""Forecast engine — ``weekday_average_v1``.

Pure, deterministic forecasting math with no database, FastAPI, or timezone
concerns. Given one item's history it predicts each horizon date. Policy is
defined in ``docs/FORECASTING.md`` §6–11, §65:

1. average the most recent 4 observations for the same weekday, else
2. average the available same-weekday observations (1–3), else
3. average the most recent 7 observations for the item, else
4. produce no forecast (item has no history).

Explicit zero observations count; missing dates are simply absent. Output is
non-negative and retains 4-decimal precision.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MODEL_VERSION = "weekday_average_v1"
HORIZON_DAYS = 7
MATCHING_WEEKDAY_HISTORY_COUNT = 4
RECENT_FALLBACK_COUNT = 7

_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class HistoricalObservation:
    business_date: date
    quantity: int


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    forecast_date: date
    predicted_quantity: Decimal


def _average(quantities: list[int]) -> Decimal:
    total = Decimal(sum(quantities))
    return (total / Decimal(len(quantities))).quantize(_QUANTUM, rounding=ROUND_HALF_UP)


class ForecastEngine:
    model_version = MODEL_VERSION

    def generate(
        self,
        history: list[HistoricalObservation],
        forecast_start_date: date,
        horizon_days: int = HORIZON_DAYS,
    ) -> list[ForecastPoint]:
        if not history:
            return []

        ordered = sorted(history, key=lambda obs: obs.business_date)
        by_weekday: dict[int, list[int]] = defaultdict(list)
        for obs in ordered:
            by_weekday[obs.business_date.weekday()].append(obs.quantity)
        recent = [obs.quantity for obs in ordered[-RECENT_FALLBACK_COUNT:]]

        points: list[ForecastPoint] = []
        for offset in range(horizon_days):
            forecast_date = forecast_start_date + timedelta(days=offset)
            matching = by_weekday.get(forecast_date.weekday())
            if matching:
                sample = matching[-MATCHING_WEEKDAY_HISTORY_COUNT:]
                predicted = _average(sample)
            else:
                predicted = _average(recent)
            points.append(ForecastPoint(forecast_date, predicted))
        return points
