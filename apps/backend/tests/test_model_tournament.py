from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}
HEADER = "date,item_name,quantity,revenue"

MODEL_NAMES = {
    "seasonal_naive",
    "seasonal_average",
    "ewma_weekday",
    "level_adjusted_seasonal_naive_v2",
    "holt_winters",
}
SELECTION_REASONS = {
    "challenger_promoted",
    "insufficient_wape_improvement",
    "inconsistent_improvement",
    "challenger_bias_regression",
    "insufficient_history",
    "baseline_only",
}


def _csv(*lines: str) -> bytes:
    return ("\n".join([HEADER, *lines]) + "\n").encode()


async def _make_location(client: AsyncClient, headers: dict[str, str] = ALICE) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=headers)
    restaurant_id = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Main", "timezone": "America/New_York"},
        headers=headers,
    )
    return location.json()["id"]


async def _upload(client: AsyncClient, location_id: str, content: bytes) -> None:
    await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("sales.csv", content, "text/csv")},
        headers=ALICE,
    )


def _history_csv(days: int) -> bytes:
    today = date.today()
    lines = [
        f"{(today - timedelta(days=days - 1 - k)).isoformat()},Cheeseburger,"
        f"{100 + (today - timedelta(days=days - 1 - k)).weekday() * 10},"
        for k in range(days)
    ]
    return _csv(*lines)


async def test_model_evaluation_by_item(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    # Two items with distinct weekly patterns so both are forecastable per-series.
    today = date.today()
    lines = []
    for k in range(70):
        day = today - timedelta(days=70 - 1 - k)
        lines.append(f"{day.isoformat()},Cheeseburger,{100 + day.weekday() * 10},")
        lines.append(f"{day.isoformat()},Fries,{200 + day.weekday() * 5},")
    await _upload(client, location_id, _csv(*lines))

    response = await client.get(
        f"/api/locations/{location_id}/model-evaluations/by-item", headers=ALICE
    )

    assert response.status_code == 200
    body = response.json()
    assert body["global_champion"] in MODEL_NAMES
    names = {item["item_name"] for item in body["items"]}
    assert names == {"Cheeseburger", "Fries"}
    for item in body["items"]:
        assert item["selected_model"] in MODEL_NAMES
        assert item["reason"] in SELECTION_REASONS
        assert {m["model_name"] for m in item["models"]} == MODEL_NAMES
        # Hybrid: an item keeps the global champion unless it clearly overrode it.
        assert item["is_override"] == (item["selected_model"] != body["global_champion"])
        if not item["is_override"]:
            assert item["selected_model"] == body["global_champion"]


async def test_by_item_tenant_isolation(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    response = await client.get(
        f"/api/locations/{location_id}/model-evaluations/by-item", headers=BOB
    )

    assert response.status_code == 404


async def test_run_and_fetch_model_evaluation(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _history_csv(70))

    response = await client.post(f"/api/locations/{location_id}/model-evaluations", headers=ALICE)

    assert response.status_code == 201
    body = response.json()
    assert {m["model_name"] for m in body["models"]} == MODEL_NAMES
    assert body["selection"]["baseline_model"] == "seasonal_naive"
    assert body["selection"]["selected_model"] in MODEL_NAMES
    assert body["selection"]["reason"] in SELECTION_REASONS
    assert sum(m["is_baseline"] for m in body["models"]) == 1
    assert sum(m["is_selected"] for m in body["models"]) == 1
    assert body["window_count"] >= 1

    baseline = next(m for m in body["models"] if m["model_name"] == "seasonal_naive")
    assert baseline["wape"] is not None
    assert baseline["rmse"] is not None
    assert baseline["bias_pct"] is not None

    # Persisted and retrievable (lineage).
    latest = await client.get(
        f"/api/locations/{location_id}/model-evaluations/latest", headers=ALICE
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == body["id"]
    assert {m["model_name"] for m in latest.json()["models"]} == MODEL_NAMES


async def test_short_history_selects_baseline(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _history_csv(10))  # non-empty, too short for windows

    response = await client.post(f"/api/locations/{location_id}/model-evaluations", headers=ALICE)

    assert response.status_code == 201
    body = response.json()
    assert body["window_count"] == 0
    assert body["selection"]["selected_model"] == "seasonal_naive"
    # No window can be built -> no scoreable challenger -> baseline is the fallback.
    assert body["selection"]["reason"] == "baseline_only"


async def test_no_history_is_422(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.post(f"/api/locations/{location_id}/model-evaluations", headers=ALICE)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_forecast_history"


async def test_latest_none_is_404(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(
        f"/api/locations/{location_id}/model-evaluations/latest", headers=ALICE
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_evaluation_not_found"


async def test_tenant_isolation(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    run = await client.post(f"/api/locations/{location_id}/model-evaluations", headers=BOB)
    latest = await client.get(f"/api/locations/{location_id}/model-evaluations/latest", headers=BOB)

    assert run.status_code == 404
    assert latest.status_code == 404
