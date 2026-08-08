"""Restaurant application logic and authorization.

Owns the transaction for restaurant creation: the restaurant and its owner
membership are committed together (``docs/API_CONTRACT.md`` §16). Tenant access
is enforced here — an inaccessible restaurant is reported as *not found* to avoid
resource enumeration (``docs/API_CONTRACT.md`` §46).
"""

from __future__ import annotations

from uuid import UUID

from app.restaurants.exceptions import RestaurantNotFoundError
from app.restaurants.models import ROLE_OWNER, Restaurant
from app.restaurants.repository import RestaurantRepository
from app.users.models import User


class RestaurantService:
    def __init__(self, repository: RestaurantRepository) -> None:
        self.repository = repository

    async def create(self, *, user: User, name: str) -> tuple[Restaurant, str]:
        restaurant = await self.repository.create(name=name)
        await self.repository.add_membership(
            restaurant_id=restaurant.id,
            user_id=user.id,
            role=ROLE_OWNER,
        )
        await self.repository.session.commit()
        await self.repository.session.refresh(restaurant)
        return restaurant, ROLE_OWNER

    async def list_for_user(self, user: User) -> list[tuple[Restaurant, str]]:
        rows = await self.repository.list_for_user(user.id)
        return [(row[0], row[1]) for row in rows]

    async def get_for_user(self, user: User, restaurant_id: UUID) -> tuple[Restaurant, str]:
        row = await self.repository.get_for_user(restaurant_id, user.id)
        if row is None:
            raise RestaurantNotFoundError()
        return row[0], row[1]
