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


def _recent_weekday_rows() -> bytes:
    today = date.today()
    return _csv(
        *(
            f"{(today - timedelta(days=7 * k)).isoformat()},Cheeseburger,{qty},"
            for k, qty in enumerate([110, 100, 90, 80])  # all predict 95
        )
    )


async def test_accuracy_with_actuals(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    today = date.today()
    await _upload(client, location_id, _recent_weekday_rows())  # forecasts 95 for +1..+7
    actuals = _csv(
        *(f"{(today + timedelta(days=d)).isoformat()},Cheeseburger,100," for d in range(1, 8))
    )
    await _upload(client, location_id, actuals)

    response = await client.get(
        f"/api/locations/{location_id}/forecast-accuracy",
        params={
            "start_date": (today + timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
        },
        headers=ALICE,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evaluated_observations"] == 7
    assert body["wape"] == "0.0500"  # 35 / 700
    assert body["mae"] == "5.0000"
    assert body["bias"] == "-5.0000"  # 95 - 100


async def test_accuracy_without_actuals(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _recent_weekday_rows())

    response = await client.get(f"/api/locations/{location_id}/forecast-accuracy", headers=ALICE)

    body = response.json()
    assert body["evaluated_observations"] == 0
    assert body["wape"] is None
    assert body["mae"] is None
    assert body["bias"] is None


async def test_accuracy_empty_location(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(f"/api/locations/{location_id}/forecast-accuracy", headers=ALICE)

    assert response.status_code == 200
    assert response.json()["evaluated_observations"] == 0


async def test_accuracy_is_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    response = await client.get(f"/api/locations/{location_id}/forecast-accuracy", headers=BOB)

    assert response.status_code == 404
