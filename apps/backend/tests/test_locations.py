from __future__ import annotations

import uuid

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}


async def _create_restaurant(client: AsyncClient, name: str, headers: dict[str, str]) -> str:
    response = await client.post("/api/restaurants", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_location(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)

    response = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=ALICE,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Downtown"
    assert body["timezone"] == "America/New_York"
    assert body["restaurant_id"] == restaurant_id
    assert body["id"]


async def test_create_location_rejects_invalid_timezone(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)

    response = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "EST-5"},
        headers=ALICE,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_duplicate_location_name_conflicts(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)
    payload = {"name": "Downtown", "timezone": "America/New_York"}

    first = await client.post(
        f"/api/restaurants/{restaurant_id}/locations", json=payload, headers=ALICE
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/restaurants/{restaurant_id}/locations", json=payload, headers=ALICE
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "duplicate_location_name"


async def test_create_location_in_foreign_restaurant_is_404(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)

    response = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=BOB,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "restaurant_not_found"


async def test_list_locations_scoped_to_restaurant(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)
    await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=ALICE,
    )

    listing = await client.get(f"/api/restaurants/{restaurant_id}/locations", headers=ALICE)

    assert listing.status_code == 200
    names = [item["name"] for item in listing.json()["items"]]
    assert names == ["Downtown"]


async def test_list_locations_foreign_restaurant_is_404(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)

    response = await client.get(f"/api/restaurants/{restaurant_id}/locations", headers=BOB)

    assert response.status_code == 404


async def test_get_location_is_tenant_isolated(client: AsyncClient) -> None:
    restaurant_id = await _create_restaurant(client, "Alice's", ALICE)
    created = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=ALICE,
    )
    location_id = created.json()["id"]

    owner_view = await client.get(f"/api/locations/{location_id}", headers=ALICE)
    assert owner_view.status_code == 200

    other_view = await client.get(f"/api/locations/{location_id}", headers=BOB)
    assert other_view.status_code == 404
    assert other_view.json()["error"]["code"] == "location_not_found"


async def test_get_unknown_location_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/locations/{uuid.uuid4()}", headers=ALICE)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "location_not_found"
