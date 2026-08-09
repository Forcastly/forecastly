from __future__ import annotations

from httpx import AsyncClient, Response

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}

HEADER = "date,item_name,quantity,revenue"


def _csv(*lines: str, header: str = HEADER) -> bytes:
    return ("\n".join([header, *lines]) + "\n").encode()


async def _make_location(client: AsyncClient, headers: dict[str, str] = ALICE) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=headers)
    restaurant_id = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Main", "timezone": "America/New_York"},
        headers=headers,
    )
    return location.json()["id"]


async def _upload(
    client: AsyncClient,
    location_id: str,
    content: bytes,
    headers: dict[str, str] = ALICE,
    filename: str = "sales.csv",
) -> Response:
    return await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": (filename, content, "text/csv")},
        headers=headers,
    )


# --- import ---------------------------------------------------------------


async def test_upload_valid_csv(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(
        client,
        location_id,
        _csv("2026-08-01,Cheeseburger,48,576.00", "2026-08-01,Fries,72,288.00"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["row_count"] == 2
    assert body["accepted_row_count"] == 2
    assert body["rejected_row_count"] == 0
    assert body["forecast_generated"] is True  # auto-run generates from the new data


async def test_uploaded_sales_are_listed(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _csv("2026-08-01,Wings,0,"))

    listing = await client.get(f"/api/locations/{location_id}/sales", headers=ALICE)

    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["item_name"] == "Wings"
    assert items[0]["quantity"] == 0
    assert items[0]["revenue"] is None  # empty revenue is unknown, not zero


async def test_upload_rejects_negative_quantity(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(client, location_id, _csv("2026-08-01,Cheeseburger,-5,"))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_sales_import"
    assert error["details"][0]["row"] == 1


async def test_upload_rejects_missing_required_column(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(client, location_id, _csv("2026-08-01,10", header="date,quantity"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_sales_import"


async def test_upload_rejects_duplicate_rows_in_file(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(
        client,
        location_id,
        _csv("2026-08-01,Cheeseburger,10,", "2026-08-01,cheeseburger,12,"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_sales_import"


async def test_upload_rejects_empty_file(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(client, location_id, b"")

    assert response.status_code == 422


async def test_duplicate_file_conflicts(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    content = _csv("2026-08-07,Cheeseburger,81,")

    first = await _upload(client, location_id, content)
    assert first.status_code == 201

    second = await _upload(client, location_id, content)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "duplicate_sales_import"


async def test_overlapping_upload_upserts(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _csv("2026-08-07,Cheeseburger,81,"), filename="a.csv")
    await _upload(client, location_id, _csv("2026-08-07,Cheeseburger,84,"), filename="b.csv")

    listing = await client.get(
        f"/api/locations/{location_id}/sales", params={"item": "Cheeseburger"}, headers=ALICE
    )

    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 84


async def test_failed_import_is_recorded(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _csv("2026-08-07,Cheeseburger,-5,"))

    imports = await client.get(f"/api/locations/{location_id}/sales/imports", headers=ALICE)

    statuses = [item["status"] for item in imports.json()["items"]]
    assert "failed" in statuses


async def test_upload_non_csv_returns_415(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await _upload(
        client, location_id, _csv("2026-08-01,Cheeseburger,10,"), filename="sales.txt"
    )

    assert response.status_code == 415


async def test_upload_too_large_returns_413(client: AsyncClient) -> None:
    from app.core.config import Settings, get_settings
    from app.main import app

    location_id = await _make_location(client)
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_bytes=10)
    try:
        response = await _upload(client, location_id, _csv("2026-08-01,Cheeseburger,48,576.00"))
    finally:
        del app.dependency_overrides[get_settings]

    assert response.status_code == 413


async def test_upload_to_foreign_location_is_404(client: AsyncClient) -> None:
    location_id = await _make_location(client, ALICE)

    response = await _upload(client, location_id, _csv("2026-08-07,Cheeseburger,10,"), headers=BOB)

    assert response.status_code == 404


# --- listing --------------------------------------------------------------


async def test_list_sales_filters(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv(
            "2026-08-01,Cheeseburger,10,",
            "2026-08-02,Cheeseburger,20,",
            "2026-08-02,Fries,30,",
        ),
    )
    url = f"/api/locations/{location_id}/sales"

    by_date = await client.get(
        url, params={"start_date": "2026-08-02", "end_date": "2026-08-02"}, headers=ALICE
    )
    assert {i["business_date"] for i in by_date.json()["items"]} == {"2026-08-02"}

    by_item = await client.get(url, params={"item": "CHEESEBURGER"}, headers=ALICE)
    names = {i["item_name"] for i in by_item.json()["items"]}
    assert names == {"Cheeseburger"}
    assert len(by_item.json()["items"]) == 2


async def test_list_sales_pagination(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv(
            "2026-08-01,Cheeseburger,10,",
            "2026-08-01,Fries,20,",
            "2026-08-01,Wings,30,",
        ),
    )
    url = f"/api/locations/{location_id}/sales"

    page1 = await client.get(url, params={"limit": 2}, headers=ALICE)
    body1 = page1.json()
    assert len(body1["items"]) == 2
    assert body1["next_cursor"]

    page2 = await client.get(
        url, params={"limit": 2, "cursor": body1["next_cursor"]}, headers=ALICE
    )
    body2 = page2.json()
    assert len(body2["items"]) == 1
    assert body2["next_cursor"] is None

    names = [i["item_name"] for i in body1["items"] + body2["items"]]
    assert names == ["Cheeseburger", "Fries", "Wings"]


async def test_list_sales_invalid_cursor_is_422(client: AsyncClient) -> None:
    location_id = await _make_location(client)

    response = await client.get(
        f"/api/locations/{location_id}/sales",
        params={"cursor": "!!!not-base64"},
        headers=ALICE,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


# --- daily totals ---------------------------------------------------------


async def test_sales_daily_totals(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv(
            "2026-08-01,Cheeseburger,48,576.00",
            "2026-08-01,Fries,72,288.00",
            "2026-08-02,Cheeseburger,50,600.00",
        ),
    )

    response = await client.get(f"/api/locations/{location_id}/sales/daily", headers=ALICE)

    assert response.status_code == 200
    items = response.json()["items"]
    # Aggregated per business date across items, oldest first.
    assert [i["business_date"] for i in items] == ["2026-08-01", "2026-08-02"]
    assert items[0]["total_quantity"] == 120  # 48 + 72
    assert float(items[0]["total_revenue"]) == 864.0  # 576 + 288
    assert items[1]["total_quantity"] == 50
    assert float(items[1]["total_revenue"]) == 600.0


async def test_sales_daily_revenue_null_when_unrecorded(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(client, location_id, _csv("2026-08-01,Wings,10,"))

    items = (
        await client.get(f"/api/locations/{location_id}/sales/daily", headers=ALICE)
    ).json()["items"]

    assert items[0]["total_quantity"] == 10
    assert items[0]["total_revenue"] is None  # missing revenue is unknown, not zero


async def test_sales_daily_filters_by_date(client: AsyncClient) -> None:
    location_id = await _make_location(client)
    await _upload(
        client,
        location_id,
        _csv("2026-08-01,Fries,10,", "2026-08-02,Fries,20,", "2026-08-03,Fries,30,"),
    )

    items = (
        await client.get(
            f"/api/locations/{location_id}/sales/daily",
            params={"start_date": "2026-08-02", "end_date": "2026-08-02"},
            headers=ALICE,
        )
    ).json()["items"]

    assert [i["business_date"] for i in items] == ["2026-08-02"]
    assert items[0]["total_quantity"] == 20


async def test_sales_daily_tenant_isolation(client: AsyncClient) -> None:
    location_id = await _make_location(client)  # Alice's
    await _upload(client, location_id, _csv("2026-08-01,Fries,10,"))

    response = await client.get(f"/api/locations/{location_id}/sales/daily", headers=BOB)

    assert response.status_code == 404  # Bob cannot read Alice's location
