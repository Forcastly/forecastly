"""Forecast model abstraction.

A ``ForecastModel`` turns one item's history into predicted points for a horizon.
Models are pure and memoryless (no ``fit`` state to persist): each ``predict``
call reads the history it is given. Crucially, callers pass history **already
sliced to the forecast origin**, and models only ever reference dates on or
before the origin — so the backtester can evaluate any model with no
model-specific branching and no look-ahead leakage.

``HistoricalObservation`` and ``ForecastPoint`` are reused from ``engine`` so all
forecasting code shares one set of value objects.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol, runtime_checkable

from app.forecasts.engine import ForecastPoint, HistoricalObservation

__all__ = [
    "SEASONAL_PERIOD_DAYS",
    "ForecastModel",
    "ForecastPoint",
    "HistoricalObservation",
    "quantize",
    "same_weekday_history",
    "seasonal_reference",
]

SEASONAL_PERIOD_DAYS = 7
_QUANTUM = Decimal("0.0001")


def quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


@runtime_checkable
class ForecastModel(Protocol):
    """Common interface every candidate model implements."""

    name: str

    def params(self) -> dict[str, object]:
        """JSON-serializable parameters, recorded for lineage/reproducibility."""
        ...

    def predict(
        self,
        history: Sequence[HistoricalObservation],
        forecast_start: date,
        horizon_days: int,
    ) -> list[ForecastPoint]:
        """Predict ``horizon_days`` starting at ``forecast_start`` (origin + 1).

        ``history`` must contain only observations available as of the origin.
        """
        ...


def seasonal_reference(
    by_date: dict[date, int],
    forecast_date: date,
    origin: date,
    period_days: int,
) -> int | None:
    """Most recent same-phase actual known at ``origin`` for ``forecast_date``.

    Steps back by whole seasonal periods until on/before the origin, then keeps
    stepping back over gaps to the latest present observation. Returns ``None``
    when no same-phase history exists (missing data is never invented). For a
    7-day period this is ``actual[t-7]`` within the first week and repeats the
    last complete week for longer horizons — always using data ≤ origin.
    """
    if not by_date:
        return None
    earliest = min(by_date)
    step = timedelta(days=period_days)

    reference = forecast_date
    while reference > origin:
        reference -= step
    while reference >= earliest:
        if reference in by_date:
            return by_date[reference]
        reference -= step
    return None


def same_weekday_history(
    by_date: dict[date, int],
    forecast_date: date,
    origin: date,
    period_days: int,
) -> list[int]:
    """Same-phase observations known at ``origin``, most recent first.

    Steps back by whole seasonal periods from the phase-aligned reference,
    collecting present observations (gaps skipped, nothing invented). The head of
    the list is ``seasonal_reference``; averaging it lowers variance vs the single
    lag.
    """
    if not by_date:
        return []
    earliest = min(by_date)
    step = timedelta(days=period_days)

    reference = forecast_date
    while reference > origin:
        reference -= step
    values: list[int] = []
    while reference >= earliest:
        if reference in by_date:
            values.append(by_date[reference])
        reference -= step
    return values
