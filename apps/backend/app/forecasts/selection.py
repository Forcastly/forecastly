"""Champion/challenger model selection.

Seasonal Naive is the baseline (safe fallback). A challenger is only promoted
when it improves aggregate WAPE by at least a configured relative margin AND does
not materially worsen bias. Anything ambiguous keeps the baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.forecasts.algorithms.base import quantize
from app.forecasts.backtesting import ModelEvaluation

DEFAULT_MIN_RELATIVE_WAPE_IMPROVEMENT = Decimal("0.05")
# Challengers whose WAPE is within this relative band of the best are treated as
# tied on accuracy; the tie is broken by lower |bias %| then RMSE. Lets a
# near-unbiased, lower-error model win over one that edges it on WAPE alone.
DEFAULT_WAPE_TIEBREAK_TOLERANCE = Decimal("0.01")
# A WAPE win is only rejected for bias when BOTH hold: the challenger's |bias %|
# worsened by more than this delta, AND its absolute |bias %| is itself large
# enough to be "clearly unacceptable" (the floor). This lets a much more accurate
# model through when its bias merely drifts within an operationally fine range.
DEFAULT_MAX_BIAS_PCT_REGRESSION = Decimal("0.02")
DEFAULT_MAX_ACCEPTABLE_BIAS_PCT = Decimal("0.05")


DEFAULT_MIN_WINDOW_WIN_RATE = Decimal("0.6667")  # ~2/3 of windows (gated exactly)


class SelectionReason(StrEnum):
    CHALLENGER_PROMOTED = "challenger_promoted"
    INSUFFICIENT_WAPE_IMPROVEMENT = "insufficient_wape_improvement"
    INCONSISTENT_IMPROVEMENT = "inconsistent_improvement"
    CHALLENGER_BIAS_REGRESSION = "challenger_bias_regression"
    INSUFFICIENT_HISTORY = "insufficient_history"
    BASELINE_ONLY = "baseline_only"


@dataclass(frozen=True, slots=True)
class ModelSelection:
    baseline_model: str
    challenger_model: str | None
    selected_model: str
    relative_wape_improvement: Decimal | None
    reason: SelectionReason
    window_win_rate: Decimal | None = None


def _abs_bias_pct(evaluation: ModelEvaluation) -> Decimal:
    value = evaluation.aggregate.bias_pct
    return abs(value) if value is not None else Decimal(0)


def _has_bias_regression(
    baseline: ModelEvaluation,
    challenger: ModelEvaluation,
    max_regression: Decimal,
    max_acceptable: Decimal,
) -> bool:
    challenger_bias = _abs_bias_pct(challenger)
    return (
        challenger_bias > _abs_bias_pct(baseline) + max_regression
        and challenger_bias > max_acceptable
    )


def select_model(
    baseline: ModelEvaluation,
    challenger: ModelEvaluation | None,
    *,
    min_relative_wape_improvement: Decimal = DEFAULT_MIN_RELATIVE_WAPE_IMPROVEMENT,
    max_bias_pct_regression: Decimal = DEFAULT_MAX_BIAS_PCT_REGRESSION,
    max_acceptable_bias_pct: Decimal = DEFAULT_MAX_ACCEPTABLE_BIAS_PCT,
) -> ModelSelection:
    if challenger is None:
        return ModelSelection(
            baseline.model_name,
            None,
            baseline.model_name,
            None,
            SelectionReason.BASELINE_ONLY,
        )

    baseline_wape = baseline.aggregate.wape
    challenger_wape = challenger.aggregate.wape
    if baseline_wape is None or challenger_wape is None or baseline_wape == 0:
        return ModelSelection(
            baseline.model_name,
            challenger.model_name,
            baseline.model_name,
            None,
            SelectionReason.INSUFFICIENT_HISTORY,
        )

    relative_improvement = quantize((baseline_wape - challenger_wape) / baseline_wape)

    if relative_improvement < min_relative_wape_improvement:
        return ModelSelection(
            baseline.model_name,
            challenger.model_name,
            baseline.model_name,
            relative_improvement,
            SelectionReason.INSUFFICIENT_WAPE_IMPROVEMENT,
        )

    if _has_bias_regression(baseline, challenger, max_bias_pct_regression, max_acceptable_bias_pct):
        return ModelSelection(
            baseline.model_name,
            challenger.model_name,
            baseline.model_name,
            relative_improvement,
            SelectionReason.CHALLENGER_BIAS_REGRESSION,
        )

    return ModelSelection(
        baseline.model_name,
        challenger.model_name,
        challenger.model_name,
        relative_improvement,
        SelectionReason.CHALLENGER_PROMOTED,
    )


def _pick_best(
    scored: list[tuple[Decimal, ModelEvaluation]],
    tiebreak_tolerance: Decimal,
) -> tuple[Decimal, ModelEvaluation]:
    """Best challenger: lowest WAPE, but among those within the tolerance band of
    the minimum WAPE, prefer lower |bias %| then lower RMSE."""
    min_wape = min(wape for wape, _ in scored)
    threshold = min_wape * (Decimal(1) + tiebreak_tolerance)
    contenders = [(wape, e) for wape, e in scored if wape <= threshold]

    def rank(item: tuple[Decimal, ModelEvaluation]) -> tuple[Decimal, Decimal]:
        _, evaluation = item
        rmse = evaluation.aggregate.rmse
        return (_abs_bias_pct(evaluation), rmse if rmse is not None else Decimal("Infinity"))

    return min(contenders, key=rank)


def _window_win_stats(
    baseline: ModelEvaluation, challenger: ModelEvaluation
) -> tuple[Decimal | None, int, int]:
    """Per-window WAPE comparison, aligned by forecast origin."""
    baseline_wape = {
        w.window.forecast_origin: w.metrics.wape
        for w in baseline.windows
        if w.metrics.wape is not None
    }
    wins = 0
    total = 0
    for window in challenger.windows:
        baseline_value = baseline_wape.get(window.window.forecast_origin)
        challenger_value = window.metrics.wape
        if baseline_value is None or challenger_value is None:
            continue
        total += 1
        if challenger_value < baseline_value:
            wins += 1
    if total == 0:
        return None, 0, 0
    return quantize(Decimal(wins) / Decimal(total)), wins, total


def select_champion(
    evaluations: list[ModelEvaluation],
    baseline_name: str,
    *,
    min_relative_wape_improvement: Decimal = DEFAULT_MIN_RELATIVE_WAPE_IMPROVEMENT,
    max_bias_pct_regression: Decimal = DEFAULT_MAX_BIAS_PCT_REGRESSION,
    max_acceptable_bias_pct: Decimal = DEFAULT_MAX_ACCEPTABLE_BIAS_PCT,
    wape_tiebreak_tolerance: Decimal = DEFAULT_WAPE_TIEBREAK_TOLERANCE,
) -> ModelSelection:
    """Pick the best challenger and gate it against the baseline.

    "Best" is lowest WAPE, but challengers within a small WAPE band are treated as
    tied and broken by lower |bias %| then RMSE. Promotion then requires a relative
    WAPE gain over the baseline, consistency across ≥ 2/3 of windows, and no bias
    regression. The baseline is the safe fallback otherwise.
    """
    baseline = next(e for e in evaluations if e.model_name == baseline_name)
    scored: list[tuple[Decimal, ModelEvaluation]] = [
        (wape, e)
        for e in evaluations
        if e.model_name != baseline_name and (wape := e.aggregate.wape) is not None
    ]
    if not scored:
        return ModelSelection(
            baseline.model_name,
            None,
            baseline.model_name,
            None,
            SelectionReason.BASELINE_ONLY,
        )
    best_wape, best = _pick_best(scored, wape_tiebreak_tolerance)

    baseline_wape = baseline.aggregate.wape
    if baseline_wape is None or baseline_wape == 0:
        return ModelSelection(
            baseline.model_name,
            best.model_name,
            baseline.model_name,
            None,
            SelectionReason.INSUFFICIENT_HISTORY,
        )

    relative_improvement = quantize((baseline_wape - best_wape) / baseline_wape)
    win_rate, wins, total = _window_win_stats(baseline, best)

    def result(selected: str, reason: SelectionReason) -> ModelSelection:
        return ModelSelection(
            baseline.model_name,
            best.model_name,
            selected,
            relative_improvement,
            reason,
            win_rate,
        )

    if relative_improvement < min_relative_wape_improvement:
        return result(baseline.model_name, SelectionReason.INSUFFICIENT_WAPE_IMPROVEMENT)
    if total == 0 or wins * 3 < total * 2:  # not consistent across ≥ 2/3 of windows
        return result(baseline.model_name, SelectionReason.INCONSISTENT_IMPROVEMENT)
    if _has_bias_regression(baseline, best, max_bias_pct_regression, max_acceptable_bias_pct):
        return result(baseline.model_name, SelectionReason.CHALLENGER_BIAS_REGRESSION)
    return result(best.model_name, SelectionReason.CHALLENGER_PROMOTED)
