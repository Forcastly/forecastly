"""Location application logic and authorization.

Location access is derived from restaurant membership: the tenant boundary lives
in the restaurants domain, so this service delegates access checks to
``RestaurantRepository`` rather than reimplementing them. Inaccessible resources
are reported as *not found* to avoid enumeration (``docs/API_CONTRACT.md`` §46).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.locations.exceptions import LocationDuplicateNameError, LocationNotFoundError
from app.locations.models import Location
from app.locations.repository import LocationRepository
from app.restaurants.exceptions import RestaurantNotFoundError
from app.restaurants.repository import RestaurantRepository
from app.users.models import User


class LocationService:
    def __init__(
        self,
        repository: LocationRepository,
        restaurant_repository: RestaurantRepository,
    ) -> None:
        self.repository = repository
        self.restaurants = restaurant_repository

    async def _require_restaurant_access(self, user: User, restaurant_id: UUID) -> None:
        if await self.restaurants.get_for_user(restaurant_id, user.id) is None:
            raise RestaurantNotFoundError()

    async def create(
        self,
        *,
        user: User,
        restaurant_id: UUID,
        name: str,
        timezone: str,
    ) -> Location:
        await self._require_restaurant_access(user, restaurant_id)
        try:
            location = await self.repository.create(
                restaurant_id=restaurant_id,
                name=name,
                timezone=timezone,
            )
            await self.repository.session.commit()
        except IntegrityError:
            await self.repository.session.rollback()
            raise LocationDuplicateNameError() from None
        await self.repository.session.refresh(location)
        return location

    async def list_for_restaurant(self, user: User, restaurant_id: UUID) -> list[Location]:
        await self._require_restaurant_access(user, restaurant_id)
        return await self.repository.list_for_restaurant(restaurant_id)

    async def get(self, user: User, location_id: UUID) -> Location:
        location = await self.repository.get(location_id)
        if location is None:
            raise LocationNotFoundError()
        # Tenant check via the owning restaurant; hide inaccessible as not-found.
        if await self.restaurants.get_for_user(location.restaurant_id, user.id) is None:
            raise LocationNotFoundError()
        return location
