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


def _thirty_five_days() -> bytes:
    today = date.today()
    lines = []
    for offset in range(35):
        day = today - timedelta(days=34 - offset)
        quantity = 100 + day.weekday() * 10  # deterministic weekday pattern
        lines.append(f"{day.isoformat()},Cheeseburger,{quantity},")
    return _csv(*lines)


async def test_backtest_scores_recent_holdout(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("sales.csv", _thirty_five_days(), "text/csv")},
        headers=ALICE,
    )

    response = await client.get(
        f"/api/locations/{location_id}/forecast-backtest",
        params={"window_days": 7},
        headers=ALICE,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 7
    assert body["evaluated_observations"] == 7  # 7 held-out days, all have actuals
    assert body["wape"] is not None
    assert body["mae"] is not None


async def test_backtest_without_history_is_422(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(f"/api/locations/{location_id}/forecast-backtest", headers=ALICE)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_forecast_history"


async def test_backtest_is_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    response = await client.get(f"/api/locations/{location_id}/forecast-backtest", headers=BOB)

    assert response.status_code == 404
