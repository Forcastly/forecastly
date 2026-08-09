from __future__ import annotations

from decimal import Decimal

from app.forecasts.backtesting import ModelEvaluation
from app.forecasts.metrics import EvaluationMetrics
from app.forecasts.selection import SelectionReason, select_model

BASELINE = "seasonal_naive"
CHALLENGER = "level_adjusted_seasonal_naive"


def _evaluation(
    name: str, wape: Decimal | None, bias_pct: Decimal = Decimal("0")
) -> ModelEvaluation:
    metrics = EvaluationMetrics(
        evaluated_observations=100,
        wape=wape,
        mae=Decimal("1"),
        rmse=Decimal("1"),
        bias=Decimal("0"),
        bias_pct=bias_pct,
    )
    return ModelEvaluation(name, {}, metrics, [], {}, {})


def test_promotes_challenger_on_sufficient_improvement() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), Decimal("-0.056"))
    challenger = _evaluation(CHALLENGER, Decimal("0.107"), Decimal("-0.020"))

    selection = select_model(baseline, challenger)

    assert selection.selected_model == CHALLENGER
    assert selection.reason is SelectionReason.CHALLENGER_PROMOTED
    assert selection.relative_wape_improvement == Decimal("0.0932")


def test_keeps_baseline_on_insufficient_improvement() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"))
    challenger = _evaluation(CHALLENGER, Decimal("0.115"))

    selection = select_model(baseline, challenger)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.INSUFFICIENT_WAPE_IMPROVEMENT


def test_rejects_challenger_with_bias_regression() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), Decimal("-0.020"))
    challenger = _evaluation(CHALLENGER, Decimal("0.090"), Decimal("0.100"))

    selection = select_model(baseline, challenger)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.CHALLENGER_BIAS_REGRESSION


def test_baseline_only_when_no_challenger() -> None:
    selection = select_model(_evaluation(BASELINE, Decimal("0.118")), None)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.BASELINE_ONLY


def test_insufficient_history_when_wape_missing() -> None:
    baseline = _evaluation(BASELINE, None)
    challenger = _evaluation(CHALLENGER, Decimal("0.10"))

    selection = select_model(baseline, challenger)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.INSUFFICIENT_HISTORY
