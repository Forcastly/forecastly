"""Restaurant persistence.

Queries are tenant-scoped by ``user_id`` (via membership) so cross-tenant reads
are structurally hard to make by accident. See ``docs/ARCHITECTURE.md`` §38–39.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.restaurants.models import Restaurant, RestaurantMembership


class RestaurantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, name: str) -> Restaurant:
        restaurant = Restaurant(name=name)
        self.session.add(restaurant)
        await self.session.flush()
        return restaurant

    async def add_membership(
        self,
        *,
        restaurant_id: UUID,
        user_id: UUID,
        role: str,
    ) -> RestaurantMembership:
        membership = RestaurantMembership(
            restaurant_id=restaurant_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def list_for_user(self, user_id: UUID) -> list[Row[tuple[Restaurant, str]]]:
        stmt = (
            select(Restaurant, RestaurantMembership.role)
            .join(RestaurantMembership, RestaurantMembership.restaurant_id == Restaurant.id)
            .where(RestaurantMembership.user_id == user_id)
            .order_by(Restaurant.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_for_user(
        self,
        restaurant_id: UUID,
        user_id: UUID,
    ) -> Row[tuple[Restaurant, str]] | None:
        stmt = (
            select(Restaurant, RestaurantMembership.role)
            .join(RestaurantMembership, RestaurantMembership.restaurant_id == Restaurant.id)
            .where(
                Restaurant.id == restaurant_id,
                RestaurantMembership.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.first()
