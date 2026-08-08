"""Location persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.locations.models import Location


class LocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, restaurant_id: UUID, name: str, timezone: str) -> Location:
        location = Location(restaurant_id=restaurant_id, name=name, timezone=timezone)
        self.session.add(location)
        await self.session.flush()
        return location

    async def list_for_restaurant(self, restaurant_id: UUID) -> list[Location]:
        stmt = (
            select(Location)
            .where(Location.restaurant_id == restaurant_id)
            .order_by(Location.created_at.desc())
        )
        return list(await self.session.scalars(stmt))

    async def get(self, location_id: UUID) -> Location | None:
        return await self.session.get(Location, location_id)
