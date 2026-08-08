from __future__ import annotations

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


async def test_sales_summary(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv(
            "2026-08-01,Cheeseburger,10,100.00",
            "2026-08-01,Fries,5,20.00",
            "2026-08-02,Cheeseburger,20,200.00",
        ),
    )

    response = await client.get(f"/api/locations/{location_id}/sales/summary", headers=ALICE)

    body = response.json()
    assert body["total_quantity"] == 35
    assert body["total_revenue"] == "320.00"
    assert body["days_with_data"] == 2


async def test_sales_summary_date_filter(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv(
            "2026-08-01,Cheeseburger,10,100.00",
            "2026-08-02,Cheeseburger,20,200.00",
        ),
    )

    response = await client.get(
        f"/api/locations/{location_id}/sales/summary",
        params={"start_date": "2026-08-02", "end_date": "2026-08-02"},
        headers=ALICE,
    )

    body = response.json()
    assert body["total_quantity"] == 20
    assert body["total_revenue"] == "200.00"
    assert body["days_with_data"] == 1


async def test_sales_summary_empty(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(f"/api/locations/{location_id}/sales/summary", headers=ALICE)

    body = response.json()
    assert body["total_quantity"] == 0
    assert body["total_revenue"] is None
    assert body["days_with_data"] == 0


async def test_sales_summary_tenant_isolation(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    response = await client.get(f"/api/locations/{location_id}/sales/summary", headers=BOB)

    assert response.status_code == 404
