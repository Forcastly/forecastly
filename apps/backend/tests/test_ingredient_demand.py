from __future__ import annotations

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}


async def _location(client: AsyncClient) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=ALICE)
    rid = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{rid}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=ALICE,
    )
    return location.json()["id"]


async def _seed_sales(client: AsyncClient, location_id: str) -> None:
    # Enough same-weekday history for the engine to forecast Cheeseburger + Wings.
    lines = ["date,item_name,quantity"]
    for week in range(4):
        day = 1 + week * 7  # 2026-08-01, 08, 15, 22 — all Saturdays
        lines.append(f"2026-08-{day:02d},Cheeseburger,80")
        lines.append(f"2026-08-{day:02d},Wings,30")
    csv = ("\n".join(lines) + "\n").encode()
    upload = await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("s.csv", csv, "text/csv")},
        headers=ALICE,
    )
    assert upload.status_code in (200, 201)


async def test_ingredient_demand_explodes_forecast(client: AsyncClient) -> None:
    location_id = await _location(client)
    await _seed_sales(client, location_id)
    # Generate a forecast (upload may auto-generate; force one to be sure).
    await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)
    # Recipe for Cheeseburger only; Wings deliberately left unmapped. Note the
    # casing differs from the sold item to prove normalization matching.
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "CHEESEBURGER", "lines": [
            {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
            {"ingredient_name": "Beef", "unit": "lb", "amount": "0.25"},
        ]},
        headers=ALICE,
    )

    demand = await client.get(f"/api/locations/{location_id}/ingredient-demand", headers=ALICE)
    assert demand.status_code == 200
    body = demand.json()

    totals = {t["name"]: t for t in body["totals"]}
    assert set(totals) == {"Bun", "Beef"}
    assert totals["Bun"]["unit"] == "ea"
    # 7 forecast days × ~80 burgers × 1 bun ≈ 560; assert the ratio Beef:Bun = 0.25.
    bun = float(totals["Bun"]["quantity"])
    beef = float(totals["Beef"]["quantity"])
    assert bun > 0
    assert abs(beef - bun * 0.25) < 0.01
    # Coverage reports Wings as unmapped.
    assert body["coverage"]["unmapped_items"] == ["Wings"]
    assert body["coverage"]["mapped_items"] == 1
    assert body["coverage"]["total_items"] == 2
    assert len(body["per_day"]) == 7


async def test_ingredient_demand_empty_without_forecast(client: AsyncClient) -> None:
    location_id = await _location(client)
    demand = await client.get(f"/api/locations/{location_id}/ingredient-demand", headers=ALICE)
    assert demand.status_code == 200
    body = demand.json()
    assert body["generated_at"] is None
    assert body["per_day"] == []
    assert body["totals"] == []
    assert body["coverage"]["total_items"] == 0
