"""Forecast accuracy metrics.

Pure math over (predicted, actual) pairs — no database or HTTP. Only pairs with a
known actual should be passed in; missing actuals are excluded upstream. See
``docs/FORECASTING.md`` §32–44.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ForecastActualPair:
    predicted: Decimal
    actual: Decimal


@dataclass(frozen=True, slots=True)
class AccuracyMetrics:
    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    bias: Decimal | None


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def compute_metrics(pairs: list[ForecastActualPair]) -> AccuracyMetrics:
    count = len(pairs)
    if count == 0:
        return AccuracyMetrics(0, None, None, None)

    absolute_error = sum((abs(p.predicted - p.actual) for p in pairs), Decimal(0))
    signed_error = sum((p.predicted - p.actual for p in pairs), Decimal(0))
    total_actual = sum((p.actual for p in pairs), Decimal(0))

    # WAPE is undefined when total actual demand is zero.
    wape = _q(absolute_error / total_actual) if total_actual != 0 else None
    mae = _q(absolute_error / count)
    bias = _q(signed_error / count)  # positive = over-forecast
    return AccuracyMetrics(count, wape, mae, bias)
