from __future__ import annotations

import uuid

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}


async def test_create_restaurant_makes_creator_owner(client: AsyncClient) -> None:
    response = await client.post(
        "/api/restaurants", json={"name": "Blue Ridge Grill"}, headers=ALICE
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Blue Ridge Grill"
    assert body["role"] == "owner"
    assert body["id"]


async def test_create_restaurant_trims_name(client: AsyncClient) -> None:
    response = await client.post(
        "/api/restaurants", json={"name": "  Downtown Diner  "}, headers=ALICE
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Downtown Diner"


async def test_create_restaurant_rejects_blank_name(client: AsyncClient) -> None:
    response = await client.post("/api/restaurants", json={"name": "   "}, headers=ALICE)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_list_returns_only_own_restaurants(client: AsyncClient) -> None:
    await client.post("/api/restaurants", json={"name": "Alice's"}, headers=ALICE)
    await client.post("/api/restaurants", json={"name": "Bob's"}, headers=BOB)

    alice_list = await client.get("/api/restaurants", headers=ALICE)

    names = [item["name"] for item in alice_list.json()["items"]]
    assert names == ["Alice's"]


async def test_get_restaurant_is_tenant_isolated(client: AsyncClient) -> None:
    created = await client.post("/api/restaurants", json={"name": "Alice's"}, headers=ALICE)
    restaurant_id = created.json()["id"]

    owner_view = await client.get(f"/api/restaurants/{restaurant_id}", headers=ALICE)
    assert owner_view.status_code == 200

    other_view = await client.get(f"/api/restaurants/{restaurant_id}", headers=BOB)
    assert other_view.status_code == 404
    assert other_view.json()["error"]["code"] == "restaurant_not_found"


async def test_get_unknown_restaurant_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/restaurants/{uuid.uuid4()}", headers=ALICE)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "restaurant_not_found"
