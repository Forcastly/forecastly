"""Recipe / ingredient persistence."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import Ingredient, Recipe, RecipeIngredient


class RecipeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- ingredients -----------------------------------------------------
    async def create_ingredient(
        self, *, location_id: UUID, name: str, name_normalized: str, unit: str
    ) -> Ingredient:
        ingredient = Ingredient(
            location_id=location_id,
            name=name,
            name_normalized=name_normalized,
            unit=unit,
        )
        self.session.add(ingredient)
        await self.session.flush()
        return ingredient

    async def get_ingredient_by_normalized(
        self, location_id: UUID, name_normalized: str
    ) -> Ingredient | None:
        stmt = select(Ingredient).where(
            Ingredient.location_id == location_id,
            Ingredient.name_normalized == name_normalized,
        )
        return await self.session.scalar(stmt)

    async def get_ingredient(
        self, location_id: UUID, ingredient_id: UUID
    ) -> Ingredient | None:
        stmt = select(Ingredient).where(
            Ingredient.location_id == location_id,
            Ingredient.id == ingredient_id,
        )
        return await self.session.scalar(stmt)

    async def list_ingredients(self, location_id: UUID) -> list[Ingredient]:
        stmt = (
            select(Ingredient)
            .where(Ingredient.location_id == location_id)
            .order_by(Ingredient.name.asc())
        )
        return list(await self.session.scalars(stmt))

    # --- recipes ---------------------------------------------------------
    async def create_recipe(
        self, *, location_id: UUID, item_name: str, item_name_normalized: str
    ) -> Recipe:
        recipe = Recipe(
            location_id=location_id,
            item_name=item_name,
            item_name_normalized=item_name_normalized,
        )
        self.session.add(recipe)
        await self.session.flush()
        return recipe

    async def add_line(
        self, *, recipe_id: UUID, ingredient_id: UUID, amount: Decimal
    ) -> RecipeIngredient:
        line = RecipeIngredient(
            recipe_id=recipe_id, ingredient_id=ingredient_id, amount=amount
        )
        self.session.add(line)
        await self.session.flush()
        return line

    async def get_recipe_by_item(
        self, location_id: UUID, item_name_normalized: str
    ) -> Recipe | None:
        stmt = select(Recipe).where(
            Recipe.location_id == location_id,
            Recipe.item_name_normalized == item_name_normalized,
        )
        return await self.session.scalar(stmt)

    async def recipe_item_normalized_set(self, location_id: UUID) -> set[str]:
        stmt = select(Recipe.item_name_normalized).where(
            Recipe.location_id == location_id
        )
        return set(await self.session.scalars(stmt))
