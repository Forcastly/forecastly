"""Forecast accuracy metrics.

Pure math over (predicted, actual) pairs — no database or HTTP. Only pairs with a
known actual should be passed in; missing actuals are excluded upstream. See
``docs/FORECASTING.md`` §32–44.

Definitions (centralized here; verified by tests):

    MAE   = mean(|forecast - actual|)
    RMSE  = sqrt(mean((forecast - actual)^2))
    Bias  = mean(forecast - actual)            # negative = under-forecast
    Bias% = sum(forecast - actual) / sum(actual)
    WAPE  = sum(|forecast - actual|) / sum(actual)

Ratio metrics (WAPE, Bias%) are ``None`` when ``sum(actual) == 0``; every metric
is ``None`` when there are no observations. No NaN/Infinity ever leaks out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
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


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Full metric set used by the backtester and model tournament.

    ``mase`` (scaled by in-sample seasonal-naive error) is filled in by the
    backtester, which knows each series' training scale; ``evaluate`` alone leaves
    it ``None``.
    """

    evaluated_observations: int
    wape: Decimal | None
    mae: Decimal | None
    rmse: Decimal | None
    bias: Decimal | None
    bias_pct: Decimal | None
    mase: Decimal | None = None


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


def evaluate(pairs: list[ForecastActualPair]) -> EvaluationMetrics:
    """Compute the full metric set over prediction/actual pairs."""
    count = len(pairs)
    if count == 0:
        return EvaluationMetrics(0, None, None, None, None, None)

    absolute_error = sum((abs(p.predicted - p.actual) for p in pairs), Decimal(0))
    signed_error = sum((p.predicted - p.actual for p in pairs), Decimal(0))
    squared_error = sum(((p.predicted - p.actual) ** 2 for p in pairs), Decimal(0))
    total_actual = sum((p.actual for p in pairs), Decimal(0))

    has_volume = total_actual != 0
    return EvaluationMetrics(
        evaluated_observations=count,
        wape=_q(absolute_error / total_actual) if has_volume else None,
        mae=_q(absolute_error / count),
        rmse=_q((squared_error / Decimal(count)).sqrt()),
        bias=_q(signed_error / count),  # negative = under-forecast
        bias_pct=_q(signed_error / total_actual) if has_volume else None,
    )


def seasonal_scale(by_date: dict[date, int], period_days: int) -> Decimal | None:
    """In-sample seasonal-naive MAE for one series: ``mean(|x_t - x_{t-period}|)``.

    The denominator for MASE. ``None`` when it can't be computed (too little
    history, or a perfectly flat series where the scale would be zero).
    """
    step = timedelta(days=period_days)
    diffs = [
        abs(quantity - by_date[day - step])
        for day, quantity in by_date.items()
        if (day - step) in by_date
    ]
    if not diffs:
        return None
    total = sum(diffs)
    if total == 0:
        return None
    return Decimal(total) / Decimal(len(diffs))
