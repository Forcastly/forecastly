from __future__ import annotations

from decimal import Decimal

from app.forecasts.metrics import ForecastActualPair, compute_metrics


def _pair(predicted: int, actual: int) -> ForecastActualPair:
    return ForecastActualPair(Decimal(predicted), Decimal(actual))


def test_wape_mae_bias() -> None:
    pairs = [_pair(90, 100), _pair(60, 50), _pair(20, 25)]

    metrics = compute_metrics(pairs)

    assert metrics.evaluated_observations == 3
    assert metrics.wape == Decimal("0.1429")  # 25 / 175
    assert metrics.mae == Decimal("8.3333")  # 25 / 3
    assert metrics.bias == Decimal("-1.6667")  # -5 / 3, negative = under-forecast


def test_wape_none_when_total_actual_zero() -> None:
    metrics = compute_metrics([_pair(2, 0), _pair(3, 0)])

    assert metrics.wape is None
    assert metrics.mae == Decimal("2.5000")
    assert metrics.bias == Decimal("2.5000")


def test_empty_yields_nulls() -> None:
    metrics = compute_metrics([])

    assert metrics.evaluated_observations == 0
    assert metrics.wape is None
    assert metrics.mae is None
    assert metrics.bias is None
