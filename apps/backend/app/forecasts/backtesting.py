"""Rolling-origin backtesting.

Simulates what Forecastly would have known at a series of historical forecast
origins and scores each candidate model over the same windows. History is loaded
once by the caller and passed in per item; for each window the backtester slices
each item's series to ``business_date <= origin`` and asks the model to predict
the horizon — so no data after an origin can influence that origin's forecast.

The whole horizon is produced from a single origin (batch forecast), matching
production behavior — not rolling one-step-ahead prediction.

Adding a new ``ForecastModel`` later requires no change here: the loop contains no
model-specific branching.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.forecasts.algorithms.base import (
    SEASONAL_PERIOD_DAYS,
    ForecastModel,
    HistoricalObservation,
)
from app.forecasts.metrics import (
    EvaluationMetrics,
    ForecastActualPair,
    evaluate,
    seasonal_scale,
)

_QUANTUM = Decimal("0.0001")


def _mase(scaled_errors: list[Decimal]) -> Decimal | None:
    if not scaled_errors:
        return None
    mean = sum(scaled_errors, Decimal(0)) / Decimal(len(scaled_errors))
    return mean.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


DEFAULT_HORIZON_DAYS = 14
DEFAULT_MIN_TRAINING_DAYS = 28
DEFAULT_NUM_WINDOWS = 8
DEFAULT_STEP_DAYS = 7


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    horizon_days: int = DEFAULT_HORIZON_DAYS
    min_training_days: int = DEFAULT_MIN_TRAINING_DAYS
    num_windows: int = DEFAULT_NUM_WINDOWS
    step_days: int = DEFAULT_STEP_DAYS


@dataclass(frozen=True, slots=True)
class BacktestWindow:
    forecast_origin: date
    train_start: date
    train_end: date
    forecast_start: date
    forecast_end: date
    horizon_days: int


@dataclass(frozen=True, slots=True)
class WindowResult:
    window: BacktestWindow
    metrics: EvaluationMetrics


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    model_name: str
    params: dict[str, object]
    aggregate: EvaluationMetrics
    windows: list[WindowResult]
    horizon_slices: dict[int, EvaluationMetrics]
    weekday_slices: dict[int, EvaluationMetrics]


class RollingOriginBacktester:
    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def build_windows(self, min_date: date, max_date: date) -> list[BacktestWindow]:
        cfg = self.config
        # Latest origin whose full horizon still lands inside the actuals.
        latest_origin = max_date - timedelta(days=cfg.horizon_days)
        windows: list[BacktestWindow] = []
        for index in range(cfg.num_windows):
            origin = latest_origin - timedelta(days=index * cfg.step_days)
            if (origin - min_date).days < cfg.min_training_days:
                break
            windows.append(
                BacktestWindow(
                    forecast_origin=origin,
                    train_start=min_date,
                    train_end=origin,
                    forecast_start=origin + timedelta(days=1),
                    forecast_end=origin + timedelta(days=cfg.horizon_days),
                    horizon_days=cfg.horizon_days,
                )
            )
        windows.reverse()  # oldest origin first
        return windows

    def evaluate(
        self,
        models: Sequence[ForecastModel],
        history_by_item: Mapping[str, Sequence[HistoricalObservation]],
    ) -> list[ModelEvaluation]:
        all_dates = [obs.business_date for series in history_by_item.values() for obs in series]
        if not all_dates:
            raise ValueError("history_by_item contains no observations")

        windows = self.build_windows(min(all_dates), max(all_dates))

        # Prepare each item's series once: ordered obs, sorted date index for
        # O(log n) slicing, and a date->quantity map for actual lookups.
        prepared: dict[str, tuple[list[HistoricalObservation], list[date], dict[date, int]]] = {}
        for item, series in history_by_item.items():
            ordered = sorted(series, key=lambda obs: obs.business_date)
            dates = [obs.business_date for obs in ordered]
            by_date = {obs.business_date: obs.quantity for obs in ordered}
            prepared[item] = (ordered, dates, by_date)

        return [self._evaluate_model(model, windows, prepared) for model in models]

    def evaluate_per_item(
        self,
        models: Sequence[ForecastModel],
        history_by_item: Mapping[str, Sequence[HistoricalObservation]],
    ) -> dict[str, list[ModelEvaluation]]:
        """Evaluate every model separately for each item, so a champion can be
        chosen per series. Each item uses windows built from its own date range."""
        results: dict[str, list[ModelEvaluation]] = {}
        for item, series in history_by_item.items():
            if not series:
                continue
            ordered = sorted(series, key=lambda obs: obs.business_date)
            dates = [obs.business_date for obs in ordered]
            by_date = {obs.business_date: obs.quantity for obs in ordered}
            windows = self.build_windows(dates[0], dates[-1])
            prepared = {item: (ordered, dates, by_date)}
            results[item] = [self._evaluate_model(model, windows, prepared) for model in models]
        return results

    def _evaluate_model(
        self,
        model: ForecastModel,
        windows: Sequence[BacktestWindow],
        prepared: Mapping[str, tuple[list[HistoricalObservation], list[date], dict[date, int]]],
    ) -> ModelEvaluation:
        all_pairs: list[ForecastActualPair] = []
        all_scaled: list[Decimal] = []
        window_results: list[WindowResult] = []
        horizon_pairs: dict[int, list[ForecastActualPair]] = defaultdict(list)
        horizon_scaled: dict[int, list[Decimal]] = defaultdict(list)
        weekday_pairs: dict[int, list[ForecastActualPair]] = defaultdict(list)
        weekday_scaled: dict[int, list[Decimal]] = defaultdict(list)

        for window in windows:
            window_pairs: list[ForecastActualPair] = []
            window_scaled: list[Decimal] = []
            for ordered, dates, by_date in prepared.values():
                cutoff = bisect_right(dates, window.forecast_origin)
                history_slice = ordered[:cutoff]  # strictly on/before the origin
                if not history_slice:
                    continue
                # In-sample seasonal-naive scale from training data only (MASE).
                slice_by_date = {o.business_date: o.quantity for o in history_slice}
                scale = seasonal_scale(slice_by_date, SEASONAL_PERIOD_DAYS)
                for point in model.predict(
                    history_slice, window.forecast_start, window.horizon_days
                ):
                    actual = by_date.get(point.forecast_date)
                    if actual is None:
                        continue
                    pair = ForecastActualPair(
                        predicted=point.predicted_quantity, actual=Decimal(actual)
                    )
                    window_pairs.append(pair)
                    all_pairs.append(pair)
                    day_ahead = (point.forecast_date - window.forecast_origin).days
                    horizon_pairs[day_ahead].append(pair)
                    weekday_pairs[point.forecast_date.weekday()].append(pair)
                    if scale is not None:
                        scaled = abs(pair.predicted - pair.actual) / scale
                        window_scaled.append(scaled)
                        all_scaled.append(scaled)
                        horizon_scaled[day_ahead].append(scaled)
                        weekday_scaled[point.forecast_date.weekday()].append(scaled)
            window_results.append(
                WindowResult(window, replace(evaluate(window_pairs), mase=_mase(window_scaled)))
            )

        return ModelEvaluation(
            model_name=model.name,
            params=model.params(),
            aggregate=replace(evaluate(all_pairs), mase=_mase(all_scaled)),
            windows=window_results,
            horizon_slices={
                k: replace(evaluate(v), mase=_mase(horizon_scaled[k]))
                for k, v in sorted(horizon_pairs.items())
            },
            weekday_slices={
                k: replace(evaluate(v), mase=_mase(weekday_scaled[k]))
                for k, v in sorted(weekday_pairs.items())
            },
        )
