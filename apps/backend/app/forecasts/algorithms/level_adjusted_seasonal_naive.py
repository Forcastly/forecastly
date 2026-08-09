"""Level-Adjusted Seasonal Naive model — the challenger.

Keeps the weekly seasonal shape of Seasonal Naive but scales it by a recent
change in demand level:

    forecast[t] = seasonal_value(t) * clamp(recent_level / previous_level, lo, hi)

where ``recent_level`` is the mean of the last 7 completed days and
``previous_level`` is the mean of the 7 days before that — both strictly on/before
the forecast origin. The clamp keeps an unusual week from producing an extreme
forecast. When the ratio can't be computed safely (insufficient history, zero
previous level, non-finite), it degrades to 1.0 — i.e. plain Seasonal Naive.
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

DEFAULT_MIN_LEVEL_RATIO = Decimal("0.85")
DEFAULT_MAX_LEVEL_RATIO = Decimal("1.15")
DEFAULT_RECENT_DAYS = 7
DEFAULT_PREVIOUS_DAYS = 7
# v2 defaults: shrink the adjustment toward 1 and ignore small level moves. Both
# reduce the variance the raw ratio injects on level-stable demand. Full-week
# windows already balance weekdays, so no separate deseasonalization is needed.
DEFAULT_SHRINKAGE = Decimal("0.5")
DEFAULT_MIN_REL_CHANGE = Decimal("0.05")


def level_ratio(
    by_date: dict[date, int],
    origin: date,
    *,
    recent_days: int,
    previous_days: int,
    min_ratio: Decimal,
    max_ratio: Decimal,
    shrinkage: Decimal = Decimal("1"),
    min_rel_change: Decimal = Decimal("0"),
) -> Decimal:
    """Clamped recent/previous demand-level ratio using only data ≤ origin.

    ``shrinkage`` pulls the ratio toward 1 (``1 + shrinkage·(raw-1)``) and
    ``min_rel_change`` gates out level moves too small to trust. Defaults
    (shrinkage 1, gate 0) reproduce the plain clamped ratio.
    """
    recent_start = origin - timedelta(days=recent_days - 1)
    previous_end = origin - timedelta(days=recent_days)
    previous_start = previous_end - timedelta(days=previous_days - 1)

    recent = [q for d, q in by_date.items() if recent_start <= d <= origin]
    previous = [q for d, q in by_date.items() if previous_start <= d <= previous_end]
    if not recent or not previous:
        return Decimal(1)

    previous_level = Decimal(sum(previous)) / Decimal(len(previous))
    if previous_level == 0:
        return Decimal(1)  # undefined ratio -> no adjustment

    raw = (Decimal(sum(recent)) / Decimal(len(recent))) / previous_level
    if not raw.is_finite():
        return Decimal(1)
    if abs(raw - Decimal(1)) < min_rel_change:
        return Decimal(1)  # insignificant level move -> no adjustment

    adjusted = Decimal(1) + shrinkage * (raw - Decimal(1))
    return min(max_ratio, max(min_ratio, adjusted))


class LevelAdjustedSeasonalNaiveModel:
    name = "level_adjusted_seasonal_naive"

    def __init__(
        self,
        *,
        seasonal_period_days: int = SEASONAL_PERIOD_DAYS,
        recent_days: int = DEFAULT_RECENT_DAYS,
        previous_days: int = DEFAULT_PREVIOUS_DAYS,
        min_level_ratio: Decimal = DEFAULT_MIN_LEVEL_RATIO,
        max_level_ratio: Decimal = DEFAULT_MAX_LEVEL_RATIO,
        shrinkage: Decimal = Decimal("1"),
        min_rel_change: Decimal = Decimal("0"),
    ) -> None:
        self.seasonal_period_days = seasonal_period_days
        self.recent_days = recent_days
        self.previous_days = previous_days
        self.min_level_ratio = min_level_ratio
        self.max_level_ratio = max_level_ratio
        self.shrinkage = shrinkage
        self.min_rel_change = min_rel_change

    def params(self) -> dict[str, object]:
        return {
            "seasonal_period_days": self.seasonal_period_days,
            "recent_days": self.recent_days,
            "previous_days": self.previous_days,
            "min_level_ratio": str(self.min_level_ratio),
            "max_level_ratio": str(self.max_level_ratio),
            "shrinkage": str(self.shrinkage),
            "min_rel_change": str(self.min_rel_change),
        }

    def predict(
        self,
        history: Sequence[HistoricalObservation],
        forecast_start: date,
        horizon_days: int,
    ) -> list[ForecastPoint]:
        by_date = {obs.business_date: obs.quantity for obs in history}
        origin = forecast_start - timedelta(days=1)
        ratio = level_ratio(
            by_date,
            origin,
            recent_days=self.recent_days,
            previous_days=self.previous_days,
            min_ratio=self.min_level_ratio,
            max_ratio=self.max_level_ratio,
            shrinkage=self.shrinkage,
            min_rel_change=self.min_rel_change,
        )

        points: list[ForecastPoint] = []
        for offset in range(horizon_days):
            forecast_date = forecast_start + timedelta(days=offset)
            reference = seasonal_reference(
                by_date, forecast_date, origin, self.seasonal_period_days
            )
            if reference is None:
                continue
            predicted = Decimal(reference) * ratio
            if predicted < 0:  # demand is non-negative
                predicted = Decimal(0)
            points.append(ForecastPoint(forecast_date, quantize(predicted)))
        return points


class LevelAdjustedSeasonalNaiveV2Model(LevelAdjustedSeasonalNaiveModel):
    """Shrunk, significance-gated level adjustment (see module defaults)."""

    name = "level_adjusted_seasonal_naive_v2"

    def __init__(
        self,
        *,
        shrinkage: Decimal = DEFAULT_SHRINKAGE,
        min_rel_change: Decimal = DEFAULT_MIN_REL_CHANGE,
        **kwargs: object,
    ) -> None:
        super().__init__(shrinkage=shrinkage, min_rel_change=min_rel_change, **kwargs)  # type: ignore[arg-type]
