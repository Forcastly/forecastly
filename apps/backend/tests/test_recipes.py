from __future__ import annotations

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}


async def _location(client: AsyncClient, headers: dict[str, str]) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=headers)
    restaurant_id = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=headers,
    )
    return location.json()["id"]


async def test_create_recipe_with_inline_ingredients(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)

    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [
                {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
                {"ingredient_name": "Beef Patty", "unit": "lb", "amount": "0.25"},
            ],
        },
        headers=ALICE,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["item_name"] == "Cheeseburger"
    assert body["item_name_normalized"] == "cheeseburger"
    lines = {line["ingredient_name"]: line for line in body["lines"]}
    assert lines["Bun"]["unit"] == "ea"
    assert lines["Bun"]["amount"] == "1.0000"
    assert lines["Beef Patty"]["amount"] == "0.2500"

    fetched = await client.get(f"/api/locations/{location_id}/recipes/cheeseburger", headers=ALICE)
    assert fetched.status_code == 200
    assert len(fetched.json()["lines"]) == 2


async def test_menu_items_report_recipe_status(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    csv = b"date,item_name,quantity\n2026-08-01,Cheeseburger,10\n2026-08-01,Fries,20\n"
    upload = await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("s.csv", csv, "text/csv")},
        headers=ALICE,
    )
    assert upload.status_code in (200, 201)
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}],
        },
        headers=ALICE,
    )

    items = await client.get(f"/api/locations/{location_id}/menu-items", headers=ALICE)
    assert items.status_code == 200
    by_name = {i["item_name_normalized"]: i["has_recipe"] for i in items.json()["items"]}
    assert by_name == {"cheeseburger": True, "fries": False}


async def test_duplicate_recipe_conflicts(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    payload = {
        "item_name": "Cheeseburger",
        "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}],
    }
    first = await client.post(f"/api/locations/{location_id}/recipes", json=payload, headers=ALICE)
    assert first.status_code == 201
    second = await client.post(f"/api/locations/{location_id}/recipes", json=payload, headers=ALICE)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "duplicate_recipe"


async def test_recipes_are_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}],
        },
        headers=ALICE,
    )
    # Bob cannot read Alice's recipes or menu items.
    assert (
        await client.get(f"/api/locations/{location_id}/menu-items", headers=BOB)
    ).status_code == 404
    assert (
        await client.get(f"/api/locations/{location_id}/recipes/cheeseburger", headers=BOB)
    ).status_code == 404


async def test_line_referencing_unknown_ingredient_id_is_404(client: AsyncClient) -> None:
    import uuid

    location_id = await _location(client, ALICE)
    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [{"ingredient_id": str(uuid.uuid4()), "amount": "1"}],
        },
        headers=ALICE,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ingredient_not_found"


async def test_duplicate_ingredient_lines_are_rejected(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [
                {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
                # Same ingredient, different display spelling — normalizes the same.
                {"ingredient_name": "  bun ", "unit": "ea", "amount": "2"},
            ],
        },
        headers=ALICE,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
