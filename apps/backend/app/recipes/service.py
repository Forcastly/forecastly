"""Recipe application logic and authorization.

Authorizes the location via ``LocationService`` (404 on inaccessible), resolves
ingredient references (existing id or inline name+unit), and persists recipes
atomically. Reads distinct menu items from sales to drive the builder.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.forecasts.repository import ForecastRepository
from app.locations.service import LocationService
from app.recipes.exceptions import (
    DuplicateRecipeError,
    DuplicateRecipeLineError,
    IngredientNotFoundError,
    RecipeNotFoundError,
)
from app.recipes.models import Ingredient, Recipe
from app.recipes.repository import RecipeRepository
from app.recipes.schemas import RecipeLineInput
from app.sales.csv import normalize_item_name
from app.sales.repository import SalesRepository
from app.users.models import User


class RecipeService:
    def __init__(
        self,
        repository: RecipeRepository,
        locations: LocationService,
        sales: SalesRepository,
        forecasts: ForecastRepository,
    ) -> None:
        self.repository = repository
        self.locations = locations
        self.sales = sales
        self.forecasts = forecasts

    @property
    def session(self):  # type: ignore[no-untyped-def]
        return self.repository.session

    async def list_menu_items(
        self, user: User, location_id: UUID
    ) -> list[tuple[str, str, bool]]:
        location = await self.locations.get(user, location_id)
        items = await self.sales.distinct_items(location.id)
        with_recipe = await self.repository.recipe_item_normalized_set(location.id)
        return [(name, norm, norm in with_recipe) for name, norm in items]

    async def list_ingredients(self, user: User, location_id: UUID) -> list[Ingredient]:
        location = await self.locations.get(user, location_id)
        return await self.repository.list_ingredients(location.id)

    async def get_recipe(
        self, user: User, location_id: UUID, item_name_normalized: str
    ) -> Recipe:
        location = await self.locations.get(user, location_id)
        recipe = await self.repository.get_recipe_by_item(
            location.id, item_name_normalized
        )
        if recipe is None:
            raise RecipeNotFoundError()
        return recipe

    async def _resolve_ingredient(
        self, location_id: UUID, line: RecipeLineInput
    ) -> Ingredient:
        if line.ingredient_id is not None:
            existing = await self.repository.get_ingredient(
                location_id, line.ingredient_id
            )
            if existing is None:
                raise IngredientNotFoundError()
            return existing
        assert line.ingredient_name is not None and line.unit is not None
        normalized = normalize_item_name(line.ingredient_name)
        existing = await self.repository.get_ingredient_by_normalized(
            location_id, normalized
        )
        if existing is not None:
            return existing  # stored unit stays authoritative
        return await self.repository.create_ingredient(
            location_id=location_id,
            name=line.ingredient_name.strip(),
            name_normalized=normalized,
            unit=line.unit.strip(),
        )

    async def create_recipe(
        self,
        *,
        user: User,
        location_id: UUID,
        item_name: str,
        lines: list[RecipeLineInput],
    ) -> Recipe:
        location = await self.locations.get(user, location_id)
        normalized = normalize_item_name(item_name)

        # Resolve every line to a concrete ingredient before writing anything.
        # Reject two lines that resolve to the same ingredient — whether by
        # repeating an ingredient_id, or by two ingredient_names that only
        # collide once normalized against the DB (a cross-type duplicate the
        # schema validator can't see) — with a clean error here, rather than
        # letting recipe_ingredients' unique constraint raise IntegrityError
        # out of add_line with no handler around it.
        resolved_ingredients: list[Ingredient] = []
        seen_ingredient_ids: set[UUID] = set()
        for line in lines:
            ingredient = await self._resolve_ingredient(location.id, line)
            if ingredient.id in seen_ingredient_ids:
                raise DuplicateRecipeLineError()
            seen_ingredient_ids.add(ingredient.id)
            resolved_ingredients.append(ingredient)

        # Only the recipe-row insert maps IntegrityError to "duplicate recipe"
        # — that's the only constraint this statement can violate. Duplicate
        # ingredient references within `lines` (both same-type and
        # cross-type) are already rejected above with their own clean error,
        # not funneled through this same-looking-but-wrong message.
        try:
            recipe = await self.repository.create_recipe(
                location_id=location.id,
                item_name=item_name.strip(),
                item_name_normalized=normalized,
            )
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateRecipeError() from None

        for line, ingredient in zip(lines, resolved_ingredients, strict=True):
            await self.repository.add_line(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                amount=line.amount,
            )
        await self.session.commit()
        return await self.get_recipe(user, location.id, normalized)

    async def update_recipe(
        self,
        *,
        user: User,
        location_id: UUID,
        recipe_id: UUID,
        lines: list[RecipeLineInput],
    ) -> Recipe:
        location = await self.locations.get(user, location_id)
        recipe = await self.repository.get_recipe(location.id, recipe_id)
        if recipe is None:
            raise RecipeNotFoundError()

        # Same resolve-then-dedup guard as create_recipe: resolve every line
        # to a concrete ingredient before touching any rows, and reject a
        # second line that resolves to an already-seen ingredient (same-type
        # or cross-type) with a clean 409 — rather than deleting the old
        # lines, then tripping the recipe_ingredients unique constraint at
        # add_line and 500ing.
        resolved_ingredients: list[Ingredient] = []
        seen_ingredient_ids: set[UUID] = set()
        for line in lines:
            ingredient = await self._resolve_ingredient(location.id, line)
            if ingredient.id in seen_ingredient_ids:
                raise DuplicateRecipeLineError()
            seen_ingredient_ids.add(ingredient.id)
            resolved_ingredients.append(ingredient)

        await self.repository.delete_lines(recipe.id)
        for line, ingredient in zip(lines, resolved_ingredients, strict=True):
            await self.repository.add_line(
                recipe_id=recipe.id, ingredient_id=ingredient.id, amount=line.amount
            )
        await self.session.commit()
        # `recipe.lines` was eager-loaded (selectin) by repository.get_recipe
        # above, before delete_lines/add_line mutated the underlying rows
        # directly (not through the relationship collection). With
        # expire_on_commit=False, that in-memory collection is never
        # invalidated by the commit, and a later query for the same identity
        # does not re-populate an already-loaded relationship. Expire it here
        # so the get_recipe() call below fetches lines fresh from the DB.
        self.session.expire(recipe, ["lines"])
        return await self.get_recipe(user, location.id, recipe.item_name_normalized)

    async def delete_recipe(
        self, *, user: User, location_id: UUID, recipe_id: UUID
    ) -> None:
        location = await self.locations.get(user, location_id)
        recipe = await self.repository.get_recipe(location.id, recipe_id)
        if recipe is None:
            raise RecipeNotFoundError()
        await self.repository.delete_recipe(recipe)
        await self.session.commit()
