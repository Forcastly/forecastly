from __future__ import annotations

from decimal import Decimal

from app.forecasts.metrics import ForecastActualPair, compute_metrics, evaluate


def _pair(predicted: int, actual: int) -> ForecastActualPair:
    return ForecastActualPair(Decimal(predicted), Decimal(actual))


def test_full_metric_set() -> None:
    # errors: -10, +10, -5 ; |err|: 10,10,5 ; sq: 100,100,25 ; actual sum 175
    metrics = evaluate([_pair(90, 100), _pair(60, 50), _pair(20, 25)])

    assert metrics.evaluated_observations == 3
    assert metrics.wape == Decimal("0.1429")  # 25 / 175
    assert metrics.mae == Decimal("8.3333")  # 25 / 3
    assert metrics.rmse == Decimal("8.6603")  # sqrt(225 / 3) = sqrt(75)
    assert metrics.bias == Decimal("-1.6667")  # -5 / 3
    assert metrics.bias_pct == Decimal("-0.0286")  # -5 / 175


def test_bias_sign_is_underforecast_when_forecast_below_actual() -> None:
    metrics = evaluate([_pair(80, 100)])

    assert metrics.bias == Decimal("-20.0000")  # negative => under-forecast
    assert metrics.bias_pct == Decimal("-0.2000")


def test_zero_total_actual_leaves_ratios_none() -> None:
    metrics = evaluate([_pair(2, 0), _pair(3, 0)])

    assert metrics.wape is None
    assert metrics.bias_pct is None
    assert metrics.mae == Decimal("2.5000")
    assert metrics.rmse == Decimal("2.5495")  # sqrt(13 / 2)
    assert metrics.bias == Decimal("2.5000")


def test_empty_is_all_none() -> None:
    metrics = evaluate([])

    assert metrics.evaluated_observations == 0
    assert metrics.wape is None
    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.bias is None
    assert metrics.bias_pct is None


def test_matches_existing_accuracy_metrics() -> None:
    pairs = [_pair(90, 100), _pair(60, 50), _pair(20, 25)]
    full = evaluate(pairs)
    legacy = compute_metrics(pairs)

    assert (full.wape, full.mae, full.bias) == (legacy.wape, legacy.mae, legacy.bias)
