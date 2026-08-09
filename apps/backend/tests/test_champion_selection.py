from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.forecasts.backtesting import (
    BacktestWindow,
    ModelEvaluation,
    WindowResult,
)
from app.forecasts.metrics import EvaluationMetrics
from app.forecasts.selection import SelectionReason, select_champion

BASELINE = "seasonal_naive"


def _metrics(wape: Decimal, bias_pct: Decimal = Decimal("0")) -> EvaluationMetrics:
    return EvaluationMetrics(100, wape, Decimal("1"), Decimal("1"), Decimal("0"), bias_pct)


def _window(origin: date, wape: Decimal) -> WindowResult:
    w = BacktestWindow(origin, origin, origin, origin, origin, 7)
    return WindowResult(w, _metrics(wape))


def _evaluation(
    name: str, wape: Decimal, window_wapes: list[Decimal], bias_pct: Decimal = Decimal("0")
) -> ModelEvaluation:
    base = date(2026, 1, 1)
    windows = [_window(base + timedelta(days=7 * i), w) for i, w in enumerate(window_wapes)]
    return ModelEvaluation(name, {}, _metrics(wape, bias_pct), windows, {}, {})


def test_promotes_consistent_challenger() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), [Decimal("0.12")] * 3)
    challenger = _evaluation("seasonal_average", Decimal("0.107"), [Decimal("0.10")] * 3)

    selection = select_champion([baseline, challenger], BASELINE)

    assert selection.selected_model == "seasonal_average"
    assert selection.reason is SelectionReason.CHALLENGER_PROMOTED
    assert selection.window_win_rate == Decimal("1")


def test_picks_best_of_several_challengers() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), [Decimal("0.12")] * 3)
    ok = _evaluation("ewma_weekday", Decimal("0.110"), [Decimal("0.11")] * 3)
    best = _evaluation("seasonal_average", Decimal("0.100"), [Decimal("0.10")] * 3)

    selection = select_champion([baseline, ok, best], BASELINE)

    assert selection.selected_model == "seasonal_average"  # lowest WAPE wins
    assert selection.challenger_model == "seasonal_average"


def test_wape_tie_broken_by_lower_bias() -> None:
    # Two challengers essentially tied on WAPE; the near-unbiased one wins even
    # though the other edges it on WAPE by a hair.
    baseline = _evaluation(BASELINE, Decimal("0.130"), [Decimal("0.13")] * 3)
    edges_wape = _evaluation(
        "seasonal_average", Decimal("0.1083"), [Decimal("0.108")] * 3, Decimal("-0.038")
    )
    low_bias = _evaluation(
        "holt_winters", Decimal("0.1084"), [Decimal("0.108")] * 3, Decimal("-0.007")
    )

    selection = select_champion([baseline, edges_wape, low_bias], BASELINE)

    assert selection.selected_model == "holt_winters"
    assert selection.reason is SelectionReason.CHALLENGER_PROMOTED


def test_rejects_inconsistent_challenger() -> None:
    # Big aggregate win driven by one window, loses the other two.
    baseline = _evaluation(
        BASELINE, Decimal("0.118"), [Decimal("0.10"), Decimal("0.10"), Decimal("0.20")]
    )
    challenger = _evaluation(
        "seasonal_average",
        Decimal("0.100"),
        [Decimal("0.11"), Decimal("0.11"), Decimal("0.05")],
    )

    selection = select_champion([baseline, challenger], BASELINE)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.INCONSISTENT_IMPROVEMENT


def test_rejects_bias_regression() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), [Decimal("0.12")] * 3, Decimal("-0.01"))
    challenger = _evaluation(
        "seasonal_average", Decimal("0.100"), [Decimal("0.10")] * 3, Decimal("0.10")
    )

    selection = select_champion([baseline, challenger], BASELINE)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.CHALLENGER_BIAS_REGRESSION


def test_baseline_only_when_no_scored_challengers() -> None:
    baseline = _evaluation(BASELINE, Decimal("0.118"), [Decimal("0.12")] * 3)
    challenger = ModelEvaluation(  # wape None -> not scoreable
        "seasonal_average",
        {},
        EvaluationMetrics(0, None, None, None, None, None),
        [],
        {},
        {},
    )

    selection = select_champion([baseline, challenger], BASELINE)

    assert selection.selected_model == BASELINE
    assert selection.reason is SelectionReason.BASELINE_ONLY
