from __future__ import annotations

import uuid
from datetime import date

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


async def _seed(client: AsyncClient, location_id: str) -> None:
    content = _csv(f"{date.today().isoformat()},Cheeseburger,50,")
    await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("sales.csv", content, "text/csv")},
        headers=ALICE,
    )


async def test_list_and_get_forecast_runs(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _seed(client, location_id)  # auto-run makes one run
    await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)  # second

    runs = await client.get(f"/api/locations/{location_id}/forecast-runs", headers=ALICE)
    items = runs.json()["items"]
    assert len(items) >= 2

    run_id = items[0]["id"]
    detail = await client.get(f"/api/forecast-runs/{run_id}", headers=ALICE)
    assert detail.status_code == 200
    assert detail.json()["run"]["id"] == run_id
    assert len(detail.json()["forecasts"]) == 7


async def test_get_unknown_run_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/forecast-runs/{uuid.uuid4()}", headers=ALICE)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_not_found"


async def test_forecast_runs_pagination(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _seed(client, location_id)  # 1 run
    for _ in range(3):
        await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)  # +3

    url = f"/api/locations/{location_id}/forecast-runs"
    page1 = await client.get(url, params={"limit": 2}, headers=ALICE)
    body1 = page1.json()
    assert len(body1["items"]) == 2
    assert body1["next_cursor"]

    page2 = await client.get(
        url, params={"limit": 2, "cursor": body1["next_cursor"]}, headers=ALICE
    )
    body2 = page2.json()
    assert len(body2["items"]) >= 1

    ids1 = {item["id"] for item in body1["items"]}
    ids2 = {item["id"] for item in body2["items"]}
    assert ids1.isdisjoint(ids2)


async def test_forecast_runs_tenant_isolation(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)
    await _seed(client, location_id)

    listing = await client.get(f"/api/locations/{location_id}/forecast-runs", headers=BOB)
    assert listing.status_code == 404

    owner_runs = await client.get(f"/api/locations/{location_id}/forecast-runs", headers=ALICE)
    run_id = owner_runs.json()["items"][0]["id"]
    detail = await client.get(f"/api/forecast-runs/{run_id}", headers=BOB)
    assert detail.status_code == 404
