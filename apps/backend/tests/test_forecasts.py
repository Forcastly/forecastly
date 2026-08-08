from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}
HEADER = "date,item_name,quantity,revenue"


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


def _recent_weekday_rows(item: str = "Cheeseburger") -> bytes:
    today = date.today()
    quantities = [110, 100, 90, 80]  # newest -> oldest
    lines = [
        f"{(today - timedelta(days=7 * k)).isoformat()},{item},{qty},"
        for k, qty in enumerate(quantities)
    ]
    return _csv(*lines)


async def test_generate_forecast(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _recent_weekday_rows())

    response = await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)

    assert response.status_code == 201
    body = response.json()
    assert body["run"]["model_version"] == "weekday_average_v1"
    assert body["run"]["horizon_days"] == 7
    assert len(body["forecasts"]) == 7

    target_date = (date.today() + timedelta(days=7)).isoformat()
    target = next(f for f in body["forecasts"] if f["forecast_date"] == target_date)
    assert target["predicted_quantity"] == "95.0000"  # (110+100+90+80)/4


async def test_generate_without_history_is_422(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_forecast_history"


async def test_generate_with_stale_data_is_422(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    old = (date.today() - timedelta(days=30)).isoformat()
    await _upload(client, location_id, _csv(f"{old},Cheeseburger,50,"))

    response = await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "stale_sales_data"


async def test_latest_forecast(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    today = date.today().isoformat()
    await _upload(client, location_id, _csv(f"{today},Cheeseburger,50,"))

    response = await client.get(f"/api/locations/{location_id}/forecasts/latest", headers=ALICE)

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["model_version"] == "weekday_average_v1"
    assert len(body["days"]) == 7
    assert body["days"][0]["items"][0]["item_name"] == "Cheeseburger"


async def test_latest_forecast_none_is_404(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(f"/api/locations/{location_id}/forecasts/latest", headers=ALICE)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_not_found"


async def test_import_auto_generates_forecast(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("sales.csv", _recent_weekday_rows(), "text/csv")},
        headers=ALICE,
    )

    assert response.json()["forecast_generated"] is True


async def test_forecast_is_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    generate = await client.post(f"/api/locations/{location_id}/forecasts", headers=BOB)
    latest = await client.get(f"/api/locations/{location_id}/forecasts/latest", headers=BOB)

    assert generate.status_code == 404
    assert latest.status_code == 404
