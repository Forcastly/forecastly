"""Location HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import SessionDep
from app.locations.repository import LocationRepository
from app.locations.schemas import (
    LocationCreate,
    LocationListResponse,
    LocationResponse,
)
from app.locations.service import LocationService
from app.restaurants.repository import RestaurantRepository
from app.users.dependencies import CurrentUser

router = APIRouter(tags=["locations"])


def get_location_service(session: SessionDep) -> LocationService:
    return LocationService(LocationRepository(session), RestaurantRepository(session))


LocationServiceDep = Annotated[LocationService, Depends(get_location_service)]


@router.post(
    "/restaurants/{restaurant_id}/locations",
    status_code=status.HTTP_201_CREATED,
    response_model=LocationResponse,
)
async def create_location(
    restaurant_id: UUID,
    body: LocationCreate,
    user: CurrentUser,
    service: LocationServiceDep,
) -> LocationResponse:
    location = await service.create(
        user=user,
        restaurant_id=restaurant_id,
        name=body.name,
        timezone=body.timezone,
    )
    return LocationResponse.model_validate(location)


@router.get(
    "/restaurants/{restaurant_id}/locations",
    response_model=LocationListResponse,
)
async def list_locations(
    restaurant_id: UUID,
    user: CurrentUser,
    service: LocationServiceDep,
) -> LocationListResponse:
    locations = await service.list_for_restaurant(user, restaurant_id)
    return LocationListResponse(items=[LocationResponse.model_validate(loc) for loc in locations])


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    user: CurrentUser,
    service: LocationServiceDep,
) -> LocationResponse:
    location = await service.get(user, location_id)
    return LocationResponse.model_validate(location)
