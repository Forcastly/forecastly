"""Recipe HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import SessionDep
from app.forecasts.repository import ForecastRepository
from app.locations.repository import LocationRepository
from app.locations.service import LocationService
from app.recipes.models import Recipe
from app.recipes.repository import RecipeRepository
from app.recipes.schemas import (
    IngredientDemandCoverage,
    IngredientDemandDay,
    IngredientDemandResponse,
    IngredientListResponse,
    IngredientQuantitySchema,
    IngredientResponse,
    MenuItem,
    MenuItemListResponse,
    RecipeCreate,
    RecipeLineResponse,
    RecipeResponse,
    RecipeUpdate,
)
from app.recipes.service import RecipeService
from app.restaurants.repository import RestaurantRepository
from app.sales.repository import SalesRepository
from app.users.dependencies import CurrentUser

router = APIRouter(tags=["recipes"])


def get_recipe_service(session: SessionDep) -> RecipeService:
    locations = LocationService(LocationRepository(session), RestaurantRepository(session))
    return RecipeService(
        RecipeRepository(session),
        locations,
        SalesRepository(session),
        ForecastRepository(session),
    )


RecipeServiceDep = Annotated[RecipeService, Depends(get_recipe_service)]


def _recipe_response(recipe: Recipe) -> RecipeResponse:
    return RecipeResponse(
        id=recipe.id,
        item_name=recipe.item_name,
        item_name_normalized=recipe.item_name_normalized,
        lines=[
            RecipeLineResponse(
                ingredient_id=line.ingredient_id,
                ingredient_name=line.ingredient.name,
                unit=line.ingredient.unit,
                amount=line.amount,
            )
            for line in recipe.lines
        ],
    )


@router.get("/locations/{location_id}/menu-items", response_model=MenuItemListResponse)
async def list_menu_items(
    location_id: UUID, user: CurrentUser, service: RecipeServiceDep
) -> MenuItemListResponse:
    rows = await service.list_menu_items(user, location_id)
    return MenuItemListResponse(
        items=[
            MenuItem(item_name=name, item_name_normalized=norm, has_recipe=has)
            for name, norm, has in rows
        ]
    )


@router.get("/locations/{location_id}/ingredients", response_model=IngredientListResponse)
async def list_ingredients(
    location_id: UUID, user: CurrentUser, service: RecipeServiceDep
) -> IngredientListResponse:
    ingredients = await service.list_ingredients(user, location_id)
    return IngredientListResponse(
        items=[IngredientResponse.model_validate(i) for i in ingredients]
    )


@router.get(
    "/locations/{location_id}/recipes/{item_name_normalized:path}",
    response_model=RecipeResponse,
)
async def get_recipe(
    location_id: UUID,
    item_name_normalized: str,
    user: CurrentUser,
    service: RecipeServiceDep,
) -> RecipeResponse:
    recipe = await service.get_recipe(user, location_id, item_name_normalized)
    return _recipe_response(recipe)


@router.post(
    "/locations/{location_id}/recipes",
    status_code=status.HTTP_201_CREATED,
    response_model=RecipeResponse,
)
async def create_recipe(
    location_id: UUID,
    body: RecipeCreate,
    user: CurrentUser,
    service: RecipeServiceDep,
) -> RecipeResponse:
    recipe = await service.create_recipe(
        user=user,
        location_id=location_id,
        item_name=body.item_name,
        lines=body.lines,
    )
    return _recipe_response(recipe)


@router.put(
    "/locations/{location_id}/recipes/{recipe_id}",
    response_model=RecipeResponse,
)
async def update_recipe(
    location_id: UUID,
    recipe_id: UUID,
    body: RecipeUpdate,
    user: CurrentUser,
    service: RecipeServiceDep,
) -> RecipeResponse:
    recipe = await service.update_recipe(
        user=user, location_id=location_id, recipe_id=recipe_id, lines=body.lines
    )
    return _recipe_response(recipe)


@router.delete(
    "/locations/{location_id}/recipes/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recipe(
    location_id: UUID,
    recipe_id: UUID,
    user: CurrentUser,
    service: RecipeServiceDep,
) -> Response:
    await service.delete_recipe(user=user, location_id=location_id, recipe_id=recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/locations/{location_id}/ingredient-demand",
    response_model=IngredientDemandResponse,
)
async def ingredient_demand(
    location_id: UUID, user: CurrentUser, service: RecipeServiceDep
) -> IngredientDemandResponse:
    run, demand = await service.ingredient_demand(user, location_id)
    return IngredientDemandResponse(
        generated_at=run.generated_at.isoformat() if run is not None else None,
        per_day=[
            IngredientDemandDay(
                date=day.date,
                ingredients=[
                    IngredientQuantitySchema(
                        ingredient_id=q.ingredient_id,
                        name=q.name,
                        unit=q.unit,
                        quantity=q.quantity,
                    )
                    for q in day.ingredients
                ],
            )
            for day in demand.per_day
        ],
        totals=[
            IngredientQuantitySchema(
                ingredient_id=q.ingredient_id, name=q.name, unit=q.unit, quantity=q.quantity
            )
            for q in demand.totals
        ],
        coverage=IngredientDemandCoverage(
            total_items=demand.total_items,
            mapped_items=demand.mapped_items,
            unmapped_items=demand.unmapped_items,
        ),
    )
