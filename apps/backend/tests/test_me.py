from __future__ import annotations

from httpx import AsyncClient


async def test_me_provisions_user(client: AsyncClient) -> None:
    response = await client.get("/api/me", headers={"X-Dev-Subject": "alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["email"]
    assert body["created_at"]


async def test_me_is_stable_for_same_identity(client: AsyncClient) -> None:
    first = await client.get("/api/me", headers={"X-Dev-Subject": "alice"})
    second = await client.get("/api/me", headers={"X-Dev-Subject": "alice"})

    assert first.json()["id"] == second.json()["id"]


async def test_me_distinguishes_identities(client: AsyncClient) -> None:
    alice = await client.get("/api/me", headers={"X-Dev-Subject": "alice"})
    bob = await client.get("/api/me", headers={"X-Dev-Subject": "bob"})

    assert alice.json()["id"] != bob.json()["id"]
