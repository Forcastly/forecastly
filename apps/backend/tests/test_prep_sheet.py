from __future__ import annotations

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}


async def _location(client: AsyncClient, headers: dict[str, str] = ALICE) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=headers)
    rid = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{rid}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=headers,
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


async def _seeded_location(client: AsyncClient) -> str:
    location_id = await _location(client)
    await _seed_sales(client, location_id)
    await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [
                {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
                {"ingredient_name": "Beef", "unit": "lb", "amount": "0.25"},
            ],
        },
        headers=ALICE,
    )
    return location_id


async def test_prep_sheet_defaults_into_the_horizon(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    response = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=ALICE)
    assert response.status_code == 200
    body = response.json()

    # The horizon starts the day after the last sales date, so today is almost
    # never inside it — the resolved date must still land on a real forecast day.
    assert body["horizon_start"] <= body["date"] <= body["horizon_end"]
    assert body["generated_at"] is not None


async def test_prep_sheet_matches_the_forecast_for_that_day(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    default = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=ALICE)
    target = default.json()["date"]

    sheet = await client.get(
        f"/api/locations/{location_id}/prep-sheet",
        params={"date": target},
        headers=ALICE,
    )
    assert sheet.status_code == 200
    body = sheet.json()
    assert body["date"] == target

    latest = await client.get(
        f"/api/locations/{location_id}/forecasts/latest", headers=ALICE
    )
    day = next(d for d in latest.json()["days"] if d["date"] == target)
    expected = {i["item_name"]: float(i["predicted_quantity"]) for i in day["items"]}
    actual = {i["item_name"]: float(i["predicted_quantity"]) for i in body["items"]}
    assert actual == expected
    assert [i["item_name"] for i in body["items"]] == sorted(actual)


async def test_prep_sheet_ingredients_match_ingredient_demand(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    default = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=ALICE)
    target = default.json()["date"]
    sheet = default.json()

    demand = await client.get(
        f"/api/locations/{location_id}/ingredient-demand", headers=ALICE
    )
    day = next(d for d in demand.json()["per_day"] if d["date"] == target)

    expected = {i["name"]: (i["unit"], float(i["quantity"])) for i in day["ingredients"]}
    actual = {i["name"]: (i["unit"], float(i["quantity"])) for i in sheet["ingredients"]}
    assert actual == expected
    assert set(actual) == {"Bun", "Beef"}


async def test_prep_sheet_coverage_is_scoped_to_the_day(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    response = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=ALICE)
    coverage = response.json()["coverage"]
    # Wings is forecast for this day but has no recipe, so it's excluded from the
    # ingredient list and reported rather than silently dropped.
    assert coverage["unmapped_items"] == ["Wings"]
    assert coverage["mapped_items"] == 1
    assert coverage["total_items"] == 2


async def test_prep_sheet_rejects_a_date_outside_the_horizon(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    response = await client.get(
        f"/api/locations/{location_id}/prep-sheet",
        params={"date": "2020-01-01"},
        headers=ALICE,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prep_sheet_date_unavailable"


async def test_prep_sheet_rejects_a_malformed_date(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    response = await client.get(
        f"/api/locations/{location_id}/prep-sheet",
        params={"date": "not-a-date"},
        headers=ALICE,
    )
    assert response.status_code == 422


async def test_prep_sheet_empty_without_a_forecast(client: AsyncClient) -> None:
    location_id = await _location(client)

    response = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=ALICE)
    assert response.status_code == 200
    body = response.json()
    assert body["date"] is None
    assert body["generated_at"] is None
    assert body["horizon_start"] is None
    assert body["horizon_end"] is None
    assert body["items"] == []
    assert body["ingredients"] == []
    assert body["coverage"]["total_items"] == 0


async def test_prep_sheet_is_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _seeded_location(client)

    response = await client.get(f"/api/locations/{location_id}/prep-sheet", headers=BOB)
    assert response.status_code == 404
