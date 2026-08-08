"""Restaurant HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import SessionDep
from app.restaurants.repository import RestaurantRepository
from app.restaurants.schemas import (
    RestaurantCreate,
    RestaurantListResponse,
    RestaurantResponse,
)
from app.restaurants.service import RestaurantService
from app.users.dependencies import CurrentUser

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_service(session: SessionDep) -> RestaurantService:
    return RestaurantService(RestaurantRepository(session))


RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RestaurantResponse)
async def create_restaurant(
    body: RestaurantCreate,
    user: CurrentUser,
    service: RestaurantServiceDep,
) -> RestaurantResponse:
    restaurant, role = await service.create(user=user, name=body.name)
    return RestaurantResponse.from_entity(restaurant, role)


@router.get("", response_model=RestaurantListResponse)
async def list_restaurants(
    user: CurrentUser,
    service: RestaurantServiceDep,
) -> RestaurantListResponse:
    rows = await service.list_for_user(user)
    return RestaurantListResponse(
        items=[RestaurantResponse.from_entity(r, role) for r, role in rows]
    )


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: UUID,
    user: CurrentUser,
    service: RestaurantServiceDep,
) -> RestaurantResponse:
    restaurant, role = await service.get_for_user(user, restaurant_id)
    return RestaurantResponse.from_entity(restaurant, role)
