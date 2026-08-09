# Ingredient Demand & Recipes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a restaurant enter recipes (menu item → ingredient amounts) and see predicted ingredient demand for the next seven days, derived from the existing item forecast.

**Architecture:** A new `recipes/` backend domain module (router → service → repository → models) following the established modular monolith. Three new tables (`ingredients`, `recipes`, `recipe_ingredients`). Ingredient demand is **derived at read time** by exploding the latest item forecast through current recipes — no new forecast tables. Frontend adds a Recipes builder screen and an Ingredients tab on the location dashboard, using the existing react-query hooks + OpenAPI-generated types.

**Tech Stack:** Python 3.14 · FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL · Pydantic v2 · uv. Frontend: Next.js 16 · React · TanStack Query · shadcn/ui · Tailwind · pnpm.

**Design spec:** `docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md` — read it first.

## Global Constraints

- **Layering:** router (HTTP only) → service (logic + authorization) → repository (DB only). Business logic must never raise `HTTPException`; raise `ForecastlyError` subclasses from `recipes/exceptions.py`.
- **Dependency direction:** `recipes` may depend on `locations`, `sales`, `forecasts`, `core`. `forecasts` must **not** import `recipes` (no cycle).
- **Tenant isolation:** every service method takes `user` and authorizes the location via `LocationService.get(user, location_id)`, which raises `LocationNotFoundError` (404) when inaccessible. Inaccessible resources are reported as 404, never 403.
- **Normalization:** normalize all item names and ingredient names with `app.sales.csv.normalize_item_name` (trim, collapse whitespace, casefold). This is the same normalizer used by sales and forecasts — recipes must match it exactly or explosion joins will silently miss.
- **IDs:** Forecastly-owned UUIDv7 via the `UUIDPrimaryKey` annotated type. Never let PostgreSQL generate keys.
- **Money/quantity precision:** amounts and predicted quantities are `Decimal` end to end; DB columns are `NUMERIC(14, 4)`. Pydantic v2 serializes `Decimal` as a JSON **string** — the frontend already parses decimal strings via `lib/format.ts` (`toNumber`).
- **Async ORM:** relationships accessed in async code must use `lazy="selectin"` (collections) or `lazy="joined"` (scalars); implicit lazy IO raises under asyncio.
- **Commits:** `feat(recipes): ...` (backend/full-stack) or `feat(frontend): ...`. Author = repo user. No co-author / AI footer (per `HANDOFF.md`).
- **Backend gate per task:** `uv run pytest` green, `uv run ruff check .` clean, `uv run pyright` clean (run from `apps/backend`).
- **Frontend gate per task:** `pnpm typecheck` and `pnpm lint` clean (run from `apps/frontend`). Before writing any Next.js code, read the relevant guide under `apps/frontend/node_modules/next/dist/docs/` — this Next.js version has breaking changes vs. training data (see `apps/frontend/AGENTS.md`).

---

## File Structure

**Backend — new module `apps/backend/app/recipes/`:**
- `models.py` — `Ingredient`, `Recipe`, `RecipeIngredient` ORM models.
- `exceptions.py` — `RecipeNotFoundError`, `DuplicateRecipeError`, `IngredientNotFoundError`.
- `schemas.py` — Pydantic request/response shapes for recipes, ingredients, menu items, ingredient demand.
- `repository.py` — `RecipeRepository` (DB access for the three tables).
- `explosion.py` — pure `explode(...)` function: forecast points × recipes → ingredient demand. No DB, no FastAPI.
- `service.py` — `RecipeService` (authorization, CRUD orchestration, calls `explode`).
- `router.py` — HTTP routes.
- `__init__.py` — empty package marker.

**Backend — modified:**
- `app/api.py` — include the recipes router.
- `app/sales/repository.py` — add `distinct_items(location_id)`.
- `tests/conftest.py` — register `app.recipes.models`; add the three tables to the TRUNCATE list.
- `alembic/versions/<new>.py` — the generated migration.

**Backend — tests (new):**
- `tests/test_recipes.py` — recipe/ingredient CRUD, tenant isolation (Tasks 1–2).
- `tests/test_explosion.py` — pure explosion-math unit tests (Task 3).
- `tests/test_ingredient_demand.py` — end-to-end ingredient-demand endpoint (Task 3).

**Frontend — new:**
- `app/locations/[locationId]/recipes/page.tsx` — Recipes screen (menu-item list + builder).
- `components/recipe-builder.tsx` — the add/edit-recipe form.
- `components/ingredient-demand-grid.tsx` — the Ingredients-tab demand grid + coverage banner.

**Frontend — modified:**
- `lib/api/client.ts` — add `apiPut`, `apiDelete`.
- `lib/api/schema.ts` — regenerated via `pnpm gen:api`.
- `lib/api/types.ts` — friendly type aliases for the new schemas.
- `lib/api/hooks.ts` — recipe + ingredient-demand hooks.
- `app/locations/[locationId]/page.tsx` — add the Ingredients tab + a link to the Recipes screen.

---

## Task 1: Recipe schema + create/read API

Establishes the three tables, the module skeleton, and the create/read half of the recipe API. Ends with a reviewer gate: "a user can create a recipe (creating ingredients inline) and read it, the menu-item list shows recipe status, and it is tenant-isolated."

**Files:**
- Create: `app/recipes/__init__.py`, `app/recipes/models.py`, `app/recipes/exceptions.py`, `app/recipes/schemas.py`, `app/recipes/repository.py`, `app/recipes/service.py`, `app/recipes/router.py`
- Create: `tests/test_recipes.py`
- Modify: `app/api.py`, `app/sales/repository.py`, `tests/conftest.py`
- Create: `alembic/versions/<generated>.py`

**Interfaces:**
- Consumes: `LocationService.get(user, location_id) -> Location`; `SalesRepository`; `ForecastRepository`; `normalize_item_name`; `UUIDPrimaryKey`, `TimestampMixin` from `app.core.db.types`; `NotFoundError`, `ConflictError` from `app.core.exceptions`.
- Produces:
  - Models `Ingredient`, `Recipe`, `RecipeIngredient` (see Step 3 for exact columns).
  - `RecipeRepository` methods: `create_ingredient(*, location_id, name, name_normalized, unit) -> Ingredient`, `get_ingredient_by_normalized(location_id, name_normalized) -> Ingredient | None`, `get_ingredient(location_id, ingredient_id) -> Ingredient | None`, `list_ingredients(location_id) -> list[Ingredient]`, `create_recipe(*, location_id, item_name, item_name_normalized) -> Recipe`, `add_line(*, recipe_id, ingredient_id, amount) -> RecipeIngredient`, `get_recipe_by_item(location_id, item_name_normalized) -> Recipe | None`, `recipe_item_normalized_set(location_id) -> set[str]`.
  - `RecipeService(repository, locations, sales, forecasts)` with `list_menu_items(user, location_id)`, `list_ingredients(user, location_id)`, `get_recipe(user, location_id, item_name_normalized)`, `create_recipe(user, location_id, item_name, lines)`.
  - `SalesRepository.distinct_items(location_id) -> list[tuple[str, str]]` (`(item_name, item_name_normalized)`, one row per normalized item, latest display spelling).
  - Routes under `/api`: `GET /locations/{id}/menu-items`, `GET /locations/{id}/ingredients`, `GET /locations/{id}/recipes/{item_name_normalized}`, `POST /locations/{id}/recipes`.

- [ ] **Step 1: Create the package marker and empty module files**

Create `app/recipes/__init__.py` (empty). Create the other module files as empty placeholders to be filled in later steps (`models.py`, `exceptions.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`).

- [ ] **Step 2: Write the failing test for recipe create + read**

Create `tests/test_recipes.py`:

```python
from __future__ import annotations

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}
BOB = {"X-Dev-Subject": "bob"}


async def _location(client: AsyncClient, headers: dict[str, str]) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=headers)
    restaurant_id = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{restaurant_id}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=headers,
    )
    return location.json()["id"]


async def test_create_recipe_with_inline_ingredients(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)

    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={
            "item_name": "Cheeseburger",
            "lines": [
                {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
                {"ingredient_name": "Beef Patty", "unit": "lb", "amount": "0.25"},
            ],
        },
        headers=ALICE,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["item_name"] == "Cheeseburger"
    assert body["item_name_normalized"] == "cheeseburger"
    lines = {line["ingredient_name"]: line for line in body["lines"]}
    assert lines["Bun"]["unit"] == "ea"
    assert lines["Bun"]["amount"] == "1.0000"
    assert lines["Beef Patty"]["amount"] == "0.2500"

    fetched = await client.get(
        f"/api/locations/{location_id}/recipes/cheeseburger", headers=ALICE
    )
    assert fetched.status_code == 200
    assert len(fetched.json()["lines"]) == 2
```

- [ ] **Step 3: Run the test to confirm it fails**

Run: `cd apps/backend && uv run pytest tests/test_recipes.py::test_create_recipe_with_inline_ingredients -v`
Expected: FAIL (404 route not found / import error).

- [ ] **Step 4: Write the ORM models**

`app/recipes/models.py`:

```python
"""Recipe, ingredient, and recipe-line persistence models.

A recipe maps one menu item (keyed by ``item_name_normalized``, matching sales
and forecasts) to ingredient amounts. Units live on the ingredient. See
``docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md`` §5.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base
from app.core.db.types import TimestampMixin, UUIDPrimaryKey


class Ingredient(TimestampMixin, Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        UniqueConstraint("location_id", "name_normalized"),
        Index("ix_ingredients_location", "location_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)


class Recipe(TimestampMixin, Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("location_id", "item_name_normalized"),
        Index("ix_recipes_location", "location_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    item_name_normalized: Mapped[str] = mapped_column(Text, nullable=False)

    lines: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RecipeIngredient(TimestampMixin, Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "ingredient_id"),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_recipe_ingredients_recipe", "recipe_id"),
        Index("ix_recipe_ingredients_ingredient", "ingredient_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    recipe: Mapped[Recipe] = relationship(back_populates="lines")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
```

- [ ] **Step 5: Register models in conftest and extend the TRUNCATE list**

In `tests/conftest.py`, add to the model imports block (near the other `import app.*.models`):

```python
import app.recipes.models  # noqa: F401
```

And prepend the three tables (children first) to the `_TABLES` tuple, before `"locations"`:

```python
_TABLES = (
    "recipe_ingredients",
    "recipes",
    "ingredients",
    "model_evaluation_windows",
    # ... existing entries unchanged ...
)
```

- [ ] **Step 6: Generate and verify the Alembic migration**

Ensure Postgres is up (`docker compose -f infra/docker-compose.yml up -d`) and the DB is current (`uv run alembic upgrade head`). Then:

Run: `cd apps/backend && uv run alembic revision --autogenerate -m "add recipes and ingredients"`

Open the generated file and verify it creates all three tables with: `ingredients` UNIQUE(location_id, name_normalized) + FK to locations `ondelete='CASCADE'`; `recipes` UNIQUE(location_id, item_name_normalized) + FK CASCADE; `recipe_ingredients` UNIQUE(recipe_id, ingredient_id) + CHECK `amount > 0` + FK to recipes `ondelete='CASCADE'` + FK to ingredients `ondelete='RESTRICT'`; and the four indexes. Confirm `down_revision` points at the current head. Then apply:

Run: `uv run alembic upgrade head`
Expected: migration applies with no error.

- [ ] **Step 7: Write the exceptions**

`app/recipes/exceptions.py`:

```python
"""Recipe domain exceptions."""

from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError


class RecipeNotFoundError(NotFoundError):
    code = "recipe_not_found"
    message = "The requested recipe was not found."


class IngredientNotFoundError(NotFoundError):
    code = "ingredient_not_found"
    message = "The referenced ingredient was not found for this location."


class DuplicateRecipeError(ConflictError):
    code = "duplicate_recipe"
    message = "A recipe already exists for this menu item."
```

- [ ] **Step 8: Write the schemas**

`app/recipes/schemas.py`:

```python
"""Recipe API schemas."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecipeLineInput(BaseModel):
    """One ingredient line. Either reference an existing ingredient by id, or
    supply a new ingredient name + unit to be created inline."""

    ingredient_id: UUID | None = None
    ingredient_name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    amount: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def _require_ingredient_ref(self) -> RecipeLineInput:
        if self.ingredient_id is None:
            if not (self.ingredient_name and self.ingredient_name.strip()):
                raise ValueError("Provide ingredient_id or ingredient_name.")
            if not (self.unit and self.unit.strip()):
                raise ValueError("A new ingredient requires a unit.")
        return self


class RecipeCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    lines: list[RecipeLineInput] = Field(min_length=1)


class RecipeUpdate(BaseModel):
    lines: list[RecipeLineInput] = Field(min_length=1)


class RecipeLineResponse(BaseModel):
    ingredient_id: UUID
    ingredient_name: str
    unit: str
    amount: Decimal


class RecipeResponse(BaseModel):
    id: UUID
    item_name: str
    item_name_normalized: str
    lines: list[RecipeLineResponse]


class IngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    unit: str


class IngredientListResponse(BaseModel):
    items: list[IngredientResponse]


class MenuItem(BaseModel):
    item_name: str
    item_name_normalized: str
    has_recipe: bool


class MenuItemListResponse(BaseModel):
    items: list[MenuItem]
```

- [ ] **Step 9: Add `distinct_items` to `SalesRepository`**

In `app/sales/repository.py`, add this method to `SalesRepository` (uses `select` already imported):

```python
    async def distinct_items(self, location_id: UUID) -> list[tuple[str, str]]:
        """One (display name, normalized) pair per normalized item, using the
        most recent display spelling. Drives the recipe menu-item picker."""
        stmt = (
            select(Sale.item_name, Sale.item_name_normalized)
            .where(Sale.location_id == location_id)
            .distinct(Sale.item_name_normalized)
            .order_by(Sale.item_name_normalized, Sale.business_date.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(name, normalized) for name, normalized in rows]
```

- [ ] **Step 10: Write the repository (create/read half)**

`app/recipes/repository.py`:

```python
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
```

- [ ] **Step 11: Write the service (create/read half)**

`app/recipes/service.py`:

```python
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
        try:
            recipe = await self.repository.create_recipe(
                location_id=location.id,
                item_name=item_name.strip(),
                item_name_normalized=normalized,
            )
            for line in lines:
                ingredient = await self._resolve_ingredient(location.id, line)
                await self.repository.add_line(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    amount=line.amount,
                )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateRecipeError() from None
        return await self.get_recipe(user, location.id, normalized)
```

Note: `get_recipe` re-fetches so the `lines` (and each line's `ingredient`) are loaded via the eager relationships for serialization.

- [ ] **Step 12: Write the router (create/read half) and a response mapper**

`app/recipes/router.py`:

```python
"""Recipe HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import SessionDep
from app.forecasts.repository import ForecastRepository
from app.locations.repository import LocationRepository
from app.locations.service import LocationService
from app.recipes.models import Recipe
from app.recipes.repository import RecipeRepository
from app.recipes.schemas import (
    IngredientListResponse,
    IngredientResponse,
    MenuItem,
    MenuItemListResponse,
    RecipeCreate,
    RecipeLineResponse,
    RecipeResponse,
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
    "/locations/{location_id}/recipes/{item_name_normalized}",
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
```

- [ ] **Step 13: Wire the router into the API**

In `app/api.py`, add the import and include:

```python
from app.recipes.router import router as recipes_router
# ...
api_router.include_router(recipes_router)
```

- [ ] **Step 14: Run the Step-2 test to confirm it passes**

Run: `cd apps/backend && uv run pytest tests/test_recipes.py::test_create_recipe_with_inline_ingredients -v`
Expected: PASS.

- [ ] **Step 15: Add the remaining create/read tests**

Append to `tests/test_recipes.py`:

```python
async def test_menu_items_report_recipe_status(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    csv = b"date,item_name,quantity\n2026-08-01,Cheeseburger,10\n2026-08-01,Fries,20\n"
    upload = await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("s.csv", csv, "text/csv")},
        headers=ALICE,
    )
    assert upload.status_code in (200, 201)
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "Cheeseburger", "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}]},
        headers=ALICE,
    )

    items = await client.get(f"/api/locations/{location_id}/menu-items", headers=ALICE)
    assert items.status_code == 200
    by_name = {i["item_name_normalized"]: i["has_recipe"] for i in items.json()["items"]}
    assert by_name == {"cheeseburger": True, "fries": False}


async def test_duplicate_recipe_conflicts(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    payload = {"item_name": "Cheeseburger", "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}]}
    first = await client.post(f"/api/locations/{location_id}/recipes", json=payload, headers=ALICE)
    assert first.status_code == 201
    second = await client.post(f"/api/locations/{location_id}/recipes", json=payload, headers=ALICE)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "duplicate_recipe"


async def test_recipes_are_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "Cheeseburger", "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}]},
        headers=ALICE,
    )
    # Bob cannot read Alice's recipes or menu items.
    assert (await client.get(f"/api/locations/{location_id}/menu-items", headers=BOB)).status_code == 404
    assert (await client.get(f"/api/locations/{location_id}/recipes/cheeseburger", headers=BOB)).status_code == 404


async def test_line_referencing_unknown_ingredient_id_is_404(client: AsyncClient) -> None:
    import uuid

    location_id = await _location(client, ALICE)
    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "Cheeseburger", "lines": [{"ingredient_id": str(uuid.uuid4()), "amount": "1"}]},
        headers=ALICE,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ingredient_not_found"
```

- [ ] **Step 16: Run the full task suite and quality gates**

Run: `cd apps/backend && uv run pytest tests/test_recipes.py -v && uv run ruff check . && uv run pyright`
Expected: all PASS/clean.

- [ ] **Step 17: Commit**

```bash
git add apps/backend/app/recipes apps/backend/app/api.py apps/backend/app/sales/repository.py \
        apps/backend/tests/conftest.py apps/backend/tests/test_recipes.py apps/backend/alembic/versions
git commit -m "feat(recipes): recipe schema + create/read API"
```

---

## Task 2: Recipe update + delete API

Completes recipe CRUD. Reviewer gate: "a user can replace a recipe's lines and delete a recipe; deleting a recipe leaves its ingredients in the catalog; update/delete are tenant-isolated."

**Files:**
- Modify: `app/recipes/repository.py`, `app/recipes/service.py`, `app/recipes/router.py`
- Modify: `tests/test_recipes.py`

**Interfaces:**
- Consumes: everything from Task 1.
- Produces:
  - `RecipeRepository.get_recipe(location_id, recipe_id) -> Recipe | None`, `RecipeRepository.replace_lines(recipe, resolved_lines)`, `RecipeRepository.delete_recipe(recipe)`.
  - `RecipeService.update_recipe(user, location_id, recipe_id, lines) -> Recipe`, `RecipeService.delete_recipe(user, location_id, recipe_id) -> None`.
  - Routes: `PUT /locations/{id}/recipes/{recipe_id}`, `DELETE /locations/{id}/recipes/{recipe_id}`.

- [ ] **Step 1: Write the failing update + delete tests**

Append to `tests/test_recipes.py`:

```python
async def _create_recipe(client: AsyncClient, location_id: str) -> dict:
    response = await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "Cheeseburger", "lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}]},
        headers=ALICE,
    )
    return response.json()


async def test_update_recipe_replaces_lines(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    recipe = await _create_recipe(client, location_id)

    updated = await client.put(
        f"/api/locations/{location_id}/recipes/{recipe['id']}",
        json={"lines": [
            {"ingredient_name": "Bun", "unit": "ea", "amount": "2"},
            {"ingredient_name": "Cheese", "unit": "slice", "amount": "2"},
        ]},
        headers=ALICE,
    )
    assert updated.status_code == 200
    lines = {line["ingredient_name"]: line["amount"] for line in updated.json()["lines"]}
    assert lines == {"Bun": "2.0000", "Cheese": "2.0000"}


async def test_delete_recipe_keeps_ingredients(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    recipe = await _create_recipe(client, location_id)

    deleted = await client.delete(
        f"/api/locations/{location_id}/recipes/{recipe['id']}", headers=ALICE
    )
    assert deleted.status_code == 204

    gone = await client.get(f"/api/locations/{location_id}/recipes/cheeseburger", headers=ALICE)
    assert gone.status_code == 404

    ingredients = await client.get(f"/api/locations/{location_id}/ingredients", headers=ALICE)
    assert "Bun" in [i["name"] for i in ingredients.json()["items"]]


async def test_update_and_delete_are_tenant_isolated(client: AsyncClient) -> None:
    location_id = await _location(client, ALICE)
    recipe = await _create_recipe(client, location_id)
    put = await client.put(
        f"/api/locations/{location_id}/recipes/{recipe['id']}",
        json={"lines": [{"ingredient_name": "Bun", "unit": "ea", "amount": "1"}]},
        headers=BOB,
    )
    assert put.status_code == 404
    delete = await client.delete(f"/api/locations/{location_id}/recipes/{recipe['id']}", headers=BOB)
    assert delete.status_code == 404
```

- [ ] **Step 2: Run to confirm they fail**

Run: `cd apps/backend && uv run pytest tests/test_recipes.py -k "update or delete" -v`
Expected: FAIL (405/404 — PUT/DELETE routes not defined).

- [ ] **Step 3: Add repository methods**

Append to `RecipeRepository` in `app/recipes/repository.py`:

```python
    async def get_recipe(self, location_id: UUID, recipe_id: UUID) -> Recipe | None:
        stmt = select(Recipe).where(
            Recipe.location_id == location_id,
            Recipe.id == recipe_id,
        )
        return await self.session.scalar(stmt)

    async def delete_lines(self, recipe_id: UUID) -> None:
        for line in list(
            await self.session.scalars(
                select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
            )
        ):
            await self.session.delete(line)
        await self.session.flush()

    async def delete_recipe(self, recipe: Recipe) -> None:
        await self.session.delete(recipe)
        await self.session.flush()
```

- [ ] **Step 4: Add service methods**

Append to `RecipeService` in `app/recipes/service.py`:

```python
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
        await self.repository.delete_lines(recipe.id)
        for line in lines:
            ingredient = await self._resolve_ingredient(location.id, line)
            await self.repository.add_line(
                recipe_id=recipe.id, ingredient_id=ingredient.id, amount=line.amount
            )
        await self.session.commit()
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
```

- [ ] **Step 5: Add router endpoints**

Append to `app/recipes/router.py` (add `RecipeUpdate` to the schemas import, and `Response` to the fastapi import):

```python
from fastapi import Response  # add to existing fastapi import line


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
```

- [ ] **Step 6: Run the tests and gates**

Run: `cd apps/backend && uv run pytest tests/test_recipes.py -v && uv run ruff check . && uv run pyright`
Expected: all PASS/clean.

- [ ] **Step 7: Commit**

```bash
git add apps/backend/app/recipes apps/backend/tests/test_recipes.py
git commit -m "feat(recipes): recipe update + delete API"
```

---

## Task 3: Ingredient-demand explosion

Adds the read-time explosion: latest item forecast × current recipes → per-day + total ingredient demand + coverage. Reviewer gate: "the endpoint returns correct ingredient totals, reports unmapped items, matches across normalization, and has a clean empty state."

**Files:**
- Create: `app/recipes/explosion.py`, `tests/test_explosion.py`, `tests/test_ingredient_demand.py`
- Modify: `app/recipes/repository.py`, `app/recipes/service.py`, `app/recipes/router.py`, `app/recipes/schemas.py`

**Interfaces:**
- Consumes: `ForecastRepository.latest_run(location_id) -> ForecastRun | None`, `ForecastRepository.list_forecasts_for_run(run_id) -> list[Forecast]` (existing); Task 1–2 repository/service.
- Produces:
  - `explosion.explode(points, recipes_by_item) -> IngredientDemand` (pure), with dataclasses `ForecastPointInput`, `RecipeLine`, `IngredientQuantity`, `DayDemand`, `IngredientDemand`.
  - `RecipeRepository.list_recipes_with_lines(location_id) -> list[Recipe]`.
  - `RecipeService.ingredient_demand(user, location_id) -> tuple[ForecastRun | None, IngredientDemand]`.
  - Route `GET /locations/{id}/ingredient-demand`.

- [ ] **Step 1: Write the failing explosion unit test**

Create `tests/test_explosion.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.recipes.explosion import ForecastPointInput, RecipeLine, explode

BUN = uuid4()
BEEF = uuid4()


def _point(day: int, item: str, name: str, qty: str) -> ForecastPointInput:
    return ForecastPointInput(
        forecast_date=date(2026, 8, day),
        item_name=name,
        item_name_normalized=item,
        predicted_quantity=Decimal(qty),
    )


def test_explode_sums_across_days_and_shared_ingredients() -> None:
    recipes = {
        "cheeseburger": [
            RecipeLine(BUN, "Bun", "ea", Decimal("1")),
            RecipeLine(BEEF, "Beef", "lb", Decimal("0.25")),
        ],
        "slider": [RecipeLine(BUN, "Bun", "ea", Decimal("0.5"))],
    }
    points = [
        _point(1, "cheeseburger", "Cheeseburger", "80"),
        _point(1, "slider", "Slider", "40"),
        _point(2, "cheeseburger", "Cheeseburger", "100"),
    ]

    demand = explode(points, recipes)

    # Day 1: Bun = 80*1 + 40*0.5 = 100; Beef = 80*0.25 = 20.
    day1 = {q.name: q.quantity for q in demand.per_day[0].ingredients}
    assert demand.per_day[0].date == date(2026, 8, 1)
    assert day1 == {"Bun": Decimal("100.0000"), "Beef": Decimal("20.0000")}
    # Totals across both days: Bun = 100 + 100 = 200; Beef = 20 + 25 = 45.
    totals = {q.name: q.quantity for q in demand.totals}
    assert totals == {"Bun": Decimal("200.0000"), "Beef": Decimal("45.0000")}
    assert demand.total_items == 2
    assert demand.mapped_items == 2
    assert demand.unmapped_items == []


def test_explode_reports_unmapped_items() -> None:
    recipes = {"cheeseburger": [RecipeLine(BUN, "Bun", "ea", Decimal("1"))]}
    points = [
        _point(1, "cheeseburger", "Cheeseburger", "10"),
        _point(1, "wings", "Wings", "30"),  # no recipe
    ]

    demand = explode(points, recipes)

    assert demand.total_items == 2
    assert demand.mapped_items == 1
    assert demand.unmapped_items == ["Wings"]
    # Wings contributes nothing.
    assert {q.name for q in demand.totals} == {"Bun"}
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd apps/backend && uv run pytest tests/test_explosion.py -v`
Expected: FAIL (module `app.recipes.explosion` does not exist).

- [ ] **Step 3: Write the pure explosion function**

`app/recipes/explosion.py`:

```python
"""Pure ingredient-demand explosion.

Given item forecast points and recipes keyed by normalized item name, produce
per-day and total ingredient demand plus coverage. No DB or FastAPI — see
``docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md`` §8.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

_QUANTIZE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ForecastPointInput:
    forecast_date: date
    item_name: str
    item_name_normalized: str
    predicted_quantity: Decimal


@dataclass(frozen=True, slots=True)
class RecipeLine:
    ingredient_id: UUID
    ingredient_name: str
    unit: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class IngredientQuantity:
    ingredient_id: UUID
    name: str
    unit: str
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class DayDemand:
    date: date
    ingredients: list[IngredientQuantity]


@dataclass(frozen=True, slots=True)
class IngredientDemand:
    per_day: list[DayDemand]
    totals: list[IngredientQuantity]
    total_items: int
    mapped_items: int
    unmapped_items: list[str]


def explode(
    points: list[ForecastPointInput],
    recipes_by_item: dict[str, list[RecipeLine]],
) -> IngredientDemand:
    # per_day[date][ingredient_id] -> quantity ; meta[ingredient_id] -> (name, unit)
    per_day: dict[date, dict[UUID, Decimal]] = {}
    totals: dict[UUID, Decimal] = {}
    meta: dict[UUID, tuple[str, str]] = {}
    mapped: set[str] = set()
    unmapped: dict[str, str] = {}  # normalized -> display

    for point in points:
        lines = recipes_by_item.get(point.item_name_normalized)
        if lines is None:
            unmapped.setdefault(point.item_name_normalized, point.item_name)
            continue
        mapped.add(point.item_name_normalized)
        day_bucket = per_day.setdefault(point.forecast_date, {})
        for line in lines:
            contribution = (point.predicted_quantity * line.amount).quantize(_QUANTIZE)
            day_bucket[line.ingredient_id] = (
                day_bucket.get(line.ingredient_id, Decimal("0")) + contribution
            )
            totals[line.ingredient_id] = (
                totals.get(line.ingredient_id, Decimal("0")) + contribution
            )
            meta[line.ingredient_id] = (line.ingredient_name, line.unit)

    def _sorted(bucket: dict[UUID, Decimal]) -> list[IngredientQuantity]:
        rows = [
            IngredientQuantity(iid, meta[iid][0], meta[iid][1], qty)
            for iid, qty in bucket.items()
        ]
        return sorted(rows, key=lambda q: q.name)

    per_day_out = [
        DayDemand(day, _sorted(per_day[day])) for day in sorted(per_day)
    ]
    total_items = len(mapped) + len(unmapped)
    return IngredientDemand(
        per_day=per_day_out,
        totals=_sorted(totals),
        total_items=total_items,
        mapped_items=len(mapped),
        unmapped_items=[unmapped[k] for k in sorted(unmapped)],
    )
```

- [ ] **Step 4: Run the unit test to confirm it passes**

Run: `cd apps/backend && uv run pytest tests/test_explosion.py -v`
Expected: PASS.

- [ ] **Step 5: Add the demand schemas**

Append to `app/recipes/schemas.py`:

```python
from datetime import date  # add to existing imports


class IngredientQuantitySchema(BaseModel):
    ingredient_id: UUID
    name: str
    unit: str
    quantity: Decimal


class IngredientDemandDay(BaseModel):
    date: date
    ingredients: list[IngredientQuantitySchema]


class IngredientDemandCoverage(BaseModel):
    total_items: int
    mapped_items: int
    unmapped_items: list[str]


class IngredientDemandResponse(BaseModel):
    generated_at: str | None
    per_day: list[IngredientDemandDay]
    totals: list[IngredientQuantitySchema]
    coverage: IngredientDemandCoverage
```

- [ ] **Step 6: Add the repository query**

Append to `RecipeRepository` in `app/recipes/repository.py`:

```python
    async def list_recipes_with_lines(self, location_id: UUID) -> list[Recipe]:
        stmt = select(Recipe).where(Recipe.location_id == location_id)
        return list(await self.session.scalars(stmt))
```

(The `lines` and each line's `ingredient` load eagerly via the relationship `lazy` settings.)

- [ ] **Step 7: Add the service method**

Append to `RecipeService` in `app/recipes/service.py` (add the imports at the top of the file):

```python
from datetime import datetime  # add to imports

from app.forecasts.models import ForecastRun  # add to imports
from app.recipes.explosion import (  # add to imports
    ForecastPointInput,
    IngredientDemand,
    RecipeLine,
    explode,
)
```

```python
    async def ingredient_demand(
        self, user: User, location_id: UUID
    ) -> tuple[ForecastRun | None, IngredientDemand]:
        location = await self.locations.get(user, location_id)
        run = await self.forecasts.latest_run(location.id)
        if run is None:
            empty = explode([], {})
            return None, empty

        forecasts = await self.forecasts.list_forecasts_for_run(run.id)
        points = [
            ForecastPointInput(
                forecast_date=f.forecast_date,
                item_name=f.item_name,
                item_name_normalized=f.item_name_normalized,
                predicted_quantity=f.predicted_quantity,
            )
            for f in forecasts
        ]
        recipes_by_item = {
            recipe.item_name_normalized: [
                RecipeLine(
                    ingredient_id=line.ingredient_id,
                    ingredient_name=line.ingredient.name,
                    unit=line.ingredient.unit,
                    amount=line.amount,
                )
                for line in recipe.lines
            ]
            for recipe in await self.repository.list_recipes_with_lines(location.id)
        }
        return run, explode(points, recipes_by_item)
```

- [ ] **Step 8: Add the router endpoint + mapper**

Append to `app/recipes/router.py` (extend the schemas import with the demand schemas):

```python
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
```

Add to the schemas import block in the router:

```python
from app.recipes.schemas import (
    # ... existing ...
    IngredientDemandCoverage,
    IngredientDemandDay,
    IngredientDemandResponse,
    IngredientQuantitySchema,
)
```

- [ ] **Step 9: Write the failing end-to-end demand test**

Create `tests/test_ingredient_demand.py`:

```python
from __future__ import annotations

from httpx import AsyncClient

ALICE = {"X-Dev-Subject": "alice"}


async def _location(client: AsyncClient) -> str:
    restaurant = await client.post("/api/restaurants", json={"name": "R"}, headers=ALICE)
    rid = restaurant.json()["id"]
    location = await client.post(
        f"/api/restaurants/{rid}/locations",
        json={"name": "Downtown", "timezone": "America/New_York"},
        headers=ALICE,
    )
    return location.json()["id"]


async def _seed_sales(client: AsyncClient, location_id: str) -> None:
    # Enough same-weekday history for the engine to forecast Cheeseburger + Wings.
    lines = ["date,item_name,quantity"]
    for week in range(4):
        day = 1 + week * 7  # 2026-08-01, 08, 15, 22 — all Saturdays
        lines.append(f"2026-08-{day:02d},Cheeseburger,80")
        lines.append(f"2026-08-{day:02d},Wings,30")
    csv = ("\n".join(lines) + "\n").encode()
    upload = await client.post(
        f"/api/locations/{location_id}/sales/imports",
        files={"file": ("s.csv", csv, "text/csv")},
        headers=ALICE,
    )
    assert upload.status_code in (200, 201)


async def test_ingredient_demand_explodes_forecast(client: AsyncClient) -> None:
    location_id = await _location(client)
    await _seed_sales(client, location_id)
    # Generate a forecast (upload may auto-generate; force one to be sure).
    await client.post(f"/api/locations/{location_id}/forecasts", headers=ALICE)
    # Recipe for Cheeseburger only; Wings deliberately left unmapped. Note the
    # casing differs from the sold item to prove normalization matching.
    await client.post(
        f"/api/locations/{location_id}/recipes",
        json={"item_name": "CHEESEBURGER", "lines": [
            {"ingredient_name": "Bun", "unit": "ea", "amount": "1"},
            {"ingredient_name": "Beef", "unit": "lb", "amount": "0.25"},
        ]},
        headers=ALICE,
    )

    demand = await client.get(f"/api/locations/{location_id}/ingredient-demand", headers=ALICE)
    assert demand.status_code == 200
    body = demand.json()

    totals = {t["name"]: t for t in body["totals"]}
    assert set(totals) == {"Bun", "Beef"}
    assert totals["Bun"]["unit"] == "ea"
    # 7 forecast days × ~80 burgers × 1 bun ≈ 560; assert the ratio Beef:Bun = 0.25.
    bun = float(totals["Bun"]["quantity"])
    beef = float(totals["Beef"]["quantity"])
    assert bun > 0
    assert abs(beef - bun * 0.25) < 0.01
    # Coverage reports Wings as unmapped.
    assert body["coverage"]["unmapped_items"] == ["Wings"]
    assert body["coverage"]["mapped_items"] == 1
    assert body["coverage"]["total_items"] == 2
    assert len(body["per_day"]) == 7


async def test_ingredient_demand_empty_without_forecast(client: AsyncClient) -> None:
    location_id = await _location(client)
    demand = await client.get(f"/api/locations/{location_id}/ingredient-demand", headers=ALICE)
    assert demand.status_code == 200
    body = demand.json()
    assert body["generated_at"] is None
    assert body["per_day"] == []
    assert body["totals"] == []
    assert body["coverage"]["total_items"] == 0
```

- [ ] **Step 10: Run the end-to-end tests**

Run: `cd apps/backend && uv run pytest tests/test_ingredient_demand.py -v`
Expected: PASS. If the forecast engine names weekdays differently, adjust the seed dates so all sampled dates share one weekday (the seed uses Saturdays). Do not weaken the assertions.

- [ ] **Step 11: Run all gates**

Run: `cd apps/backend && uv run pytest && uv run ruff check . && uv run pyright`
Expected: all green (the full suite, including the pre-existing 136 tests).

- [ ] **Step 12: Commit**

```bash
git add apps/backend/app/recipes apps/backend/tests/test_explosion.py apps/backend/tests/test_ingredient_demand.py
git commit -m "feat(recipes): ingredient-demand explosion endpoint"
```

---

## Task 4: Frontend API layer

Adds PUT/DELETE to the client, regenerates OpenAPI types, and exposes typed hooks for recipes + ingredient demand. Reviewer gate: "the new hooks compile and are typed against the real backend schema."

**Files:**
- Modify: `lib/api/client.ts`, `lib/api/types.ts`, `lib/api/hooks.ts`
- Regenerate: `lib/api/schema.ts`

**Interfaces:**
- Consumes: backend routes from Tasks 1–3.
- Produces: `apiPut`, `apiDelete`; type aliases `MenuItemList`, `IngredientList`, `Recipe`, `IngredientDemand`; hooks `useMenuItems`, `useIngredients`, `useRecipe`, `useSaveRecipe`, `useDeleteRecipe`, `useIngredientDemand`.

- [ ] **Step 1: Add `apiPut` and `apiDelete` to the client**

In `lib/api/client.ts`, after `apiPost`:

```typescript
export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}
```

- [ ] **Step 2: Regenerate the OpenAPI schema types**

Start the backend (`cd apps/backend && uv run uvicorn app.main:app` in another shell), then:

Run: `cd apps/frontend && pnpm gen:api`
Expected: `lib/api/schema.ts` updates and now contains `RecipeResponse`, `MenuItemListResponse`, `IngredientListResponse`, `IngredientDemandResponse`, etc. Verify with `grep IngredientDemandResponse lib/api/schema.ts`.

- [ ] **Step 3: Add friendly type aliases**

Append to `lib/api/types.ts` (before `ApiErrorDetail`):

```typescript
export type MenuItem = Schemas["MenuItem"];
export type MenuItemList = Schemas["MenuItemListResponse"];
export type Ingredient = Schemas["IngredientResponse"];
export type IngredientList = Schemas["IngredientListResponse"];
export type Recipe = Schemas["RecipeResponse"];
export type RecipeLine = Schemas["RecipeLineResponse"];
export type IngredientDemand = Schemas["IngredientDemandResponse"];
export type IngredientDemandDay = Schemas["IngredientDemandDay"];
export type IngredientQuantity = Schemas["IngredientQuantitySchema"];
```

- [ ] **Step 4: Add the hooks**

In `lib/api/hooks.ts`, extend the `apiPost` import to `import { ApiError, apiDelete, apiGet, apiPost, apiPut, apiUpload, qs } from "./client";` and the type import with the new aliases, then append:

```typescript
export function useMenuItems(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "menu-items"],
    queryFn: () => apiGet<MenuItemList>(`/api/locations/${locationId}/menu-items`),
  });
}

export function useIngredients(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "ingredients"],
    queryFn: () => apiGet<IngredientList>(`/api/locations/${locationId}/ingredients`),
  });
}

export function useRecipe(locationId: string, itemNormalized: string | undefined) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "recipe", itemNormalized],
    queryFn: async () => {
      try {
        return await apiGet<Recipe>(
          `/api/locations/${locationId}/recipes/${itemNormalized}`,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled: Boolean(itemNormalized),
  });
}

type RecipeLinePayload = {
  ingredient_id?: string;
  ingredient_name?: string;
  unit?: string;
  amount: string;
};

export function useSaveRecipe(locationId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { recipeId?: string; itemName: string; lines: RecipeLinePayload[] }) =>
      input.recipeId
        ? apiPut<Recipe>(`/api/locations/${locationId}/recipes/${input.recipeId}`, {
            lines: input.lines,
          })
        : apiPost<Recipe>(`/api/locations/${locationId}/recipes`, {
            item_name: input.itemName,
            lines: input.lines,
          }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [scope, "locations", locationId] }),
  });
}

export function useDeleteRecipe(locationId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recipeId: string) =>
      apiDelete<void>(`/api/locations/${locationId}/recipes/${recipeId}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [scope, "locations", locationId] }),
  });
}

export function useIngredientDemand(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "ingredient-demand"],
    queryFn: () =>
      apiGet<IngredientDemand>(`/api/locations/${locationId}/ingredient-demand`),
  });
}
```

Add `IngredientDemand`, `IngredientList`, `MenuItemList`, `Recipe` to the `import type { ... } from "./types";` block.

- [ ] **Step 5: Verify types + lint**

Run: `cd apps/frontend && pnpm typecheck && pnpm lint`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/lib/api
git commit -m "feat(frontend): recipe + ingredient-demand API hooks"
```

---

## Task 5: Recipes screen + builder

Adds the Recipes page (menu-item list) and the in-app builder form. Reviewer gate: "a user can open Recipes, pick a menu item, add/edit ingredient rows, and save."

**Files:**
- Create: `app/locations/[locationId]/recipes/page.tsx`, `components/recipe-builder.tsx`
- Modify: `app/locations/[locationId]/page.tsx` (add a "Recipes" link next to "Sales")

**Interfaces:**
- Consumes: `useMenuItems`, `useIngredients`, `useRecipe`, `useSaveRecipe`, `useDeleteRecipe` from Task 4; UI primitives in `components/ui/*`; `ApiError`.
- Produces: the Recipes route and `RecipeBuilder` component.

Before writing, read `apps/frontend/node_modules/next/dist/docs/` for the current routing/`"use client"` conventions (see Global Constraints).

- [ ] **Step 1: Build the `RecipeBuilder` component**

Create `components/recipe-builder.tsx`: a client component that takes `{ locationId, itemName, itemNormalized }`, loads the existing recipe via `useRecipe`, and renders editable ingredient rows (ingredient name autocomplete via `useIngredients`, amount input, unit input enabled only for new ingredients). "+ add ingredient" appends a blank row; each row has a remove button. "Save recipe" calls `useSaveRecipe` and toasts success/error via `sonner`. Model the layout, spacing, and teal/amber styling on the existing dashboard components (`components/forecast-grid.tsx`, `components/ui/input.tsx`, `components/ui/button.tsx`). Payload rows: send `{ ingredient_id, amount }` for rows bound to an existing ingredient, or `{ ingredient_name, unit, amount }` for new ones; `amount` is sent as a string.

- [ ] **Step 2: Build the Recipes page**

Create `app/locations/[locationId]/recipes/page.tsx`: a `"use client"` page that reads `locationId` from `useParams`, lists menu items from `useMenuItems` with a *Has recipe* / *No recipe* badge (`components/ui/badge.tsx`), sorted so *No recipe* items are on top. Selecting an item shows the `RecipeBuilder` for it (inline panel or a dialog via `components/ui/dialog.tsx`). Include a back link to the dashboard, mirroring the header pattern in `app/locations/[locationId]/page.tsx` (lines 95–113). Show an `EmptyState` when there are no menu items (prompt to upload sales first).

- [ ] **Step 3: Add a Recipes link on the dashboard header**

In `app/locations/[locationId]/page.tsx`, next to the existing "Sales" link (lines 115–120), add:

```tsx
<Link
  href={`/locations/${locationId}/recipes`}
  className={buttonVariants({ variant: "outline" })}
>
  Recipes
</Link>
```

- [ ] **Step 4: Verify + manual check**

Run: `cd apps/frontend && pnpm typecheck && pnpm lint`
Then run the app (`pnpm dev`, backend up) and manually: upload sales → open Recipes → build a recipe with one existing + one new ingredient → save → reopen and confirm it persisted → edit amounts → save.
Expected: typecheck/lint clean; manual flow works.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/app/locations apps/frontend/components/recipe-builder.tsx
git commit -m "feat(frontend): recipes builder screen"
```

---

## Task 6: Ingredients tab + coverage

Adds the Ingredients tab to the dashboard showing the 7-day demand grid and the coverage banner. Reviewer gate: "the dashboard shows predicted ingredient demand per day and total, and surfaces items with no recipe."

**Files:**
- Create: `components/ingredient-demand-grid.tsx`
- Modify: `app/locations/[locationId]/page.tsx`
- Modify: `HANDOFF.md` (note the new feature + follow-on specs)

**Interfaces:**
- Consumes: `useIngredientDemand` from Task 4; `formatQty`, `formatBusinessDate` from `lib/format.ts`; `components/ui/table.tsx`, `components/ui/card.tsx`.
- Produces: `IngredientDemandGrid` component + the Ingredients tab.

- [ ] **Step 1: Build the `IngredientDemandGrid` component**

Create `components/ingredient-demand-grid.tsx` (`"use client"`), props `{ locationId }`. Uses `useIngredientDemand`. Renders:
- A **coverage banner** when `coverage.unmapped_items.length > 0`: a non-blocking notice (amber, matching the design system) reading e.g. `"3 of 12 forecast items have no recipe and aren't included: Wings, Shake, Side Salad."` with a link to `/locations/${locationId}/recipes`.
- A **totals card**: each ingredient with its 7-day total via `formatQty(quantity)` + unit.
- A **per-day table**: rows = ingredients, columns = the seven `per_day` dates (header via `formatBusinessDate(day.date)`), cells `formatQty(quantity)`. Since not every ingredient appears every day, index by ingredient id per day and render `—` (via `formatQty(null)`) for gaps. Wrap the table in an `overflow-x-auto` container.
- Loading (`Skeleton`) and empty (`EmptyState`: "No forecast yet — upload sales to see ingredient demand") states, mirroring the dashboard's existing patterns.

- [ ] **Step 2: Add the Ingredients tab**

In `app/locations/[locationId]/page.tsx`:
- Import `IngredientDemandGrid`.
- Add a third trigger to `TabsList` (after line 145): `<TabsTrigger value="ingredients">Ingredients</TabsTrigger>`.
- Add the matching content after the forecast `TabsContent` (after line 168):

```tsx
<TabsContent value="ingredients" className="space-y-6 pt-2">
  <div className="flex flex-wrap items-center justify-between gap-3">
    <h2 className="font-heading text-2xl font-semibold tracking-tight">
      Ingredient demand
    </h2>
  </div>
  <IngredientDemandGrid locationId={locationId} />
</TabsContent>
```

- [ ] **Step 3: Verify + manual check**

Run: `cd apps/frontend && pnpm typecheck && pnpm lint`
Then manually (backend up, sales + at least one recipe present, forecast generated): open the dashboard → Ingredients tab → confirm per-day grid + totals show, units render, and leaving one sold item without a recipe shows the coverage banner.
Expected: typecheck/lint clean; manual flow works.

- [ ] **Step 4: Update the handoff doc**

In `HANDOFF.md`, under "Status", note that ingredient-level demand (recipes + explosion) shipped, and under "Next steps" list the follow-on specs: inventory (on-hand + par), then purchasing (suppliers, pack sizes, POs). Reference the spec at `docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md`.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/components/ingredient-demand-grid.tsx apps/frontend/app/locations/[locationId]/page.tsx HANDOFF.md
git commit -m "feat(frontend): ingredient demand tab + coverage"
```

---

## Self-Review

**Spec coverage** (spec §→task):
- §2/§5 data model (3 tables) → Task 1 (models + migration).
- §3 in-app builder → Tasks 5.
- §4 ingredient catalog + inline creation → Task 1 (`_resolve_ingredient`).
- §6 recipe API (CRUD + menu-items + ingredients) → Tasks 1–2.
- §8 explosion (derived, read-time) → Task 3.
- §9 dashboard tab + coverage banner → Task 6.
- §10 testing (tenant isolation, uniqueness, inline creation, explosion math, coverage, normalization parity, empty states) → Task 1 tests (isolation, uniqueness, inline, menu-item status, unknown ingredient), Task 2 tests (update/delete/isolation/ingredient persists), Task 3 tests (explosion math, shared ingredient, unmapped, e2e with normalization parity + empty).
- §11 non-goals → nothing built (inventory/suppliers/PO/conversion/sub-recipes/waste/versioning absent by construction).

**Placeholder scan:** Task 5 Step 1–2 describe the builder/page in prose rather than full code — this is deliberate for UI-heavy components with no automated tests; the description names exact hooks, props, payload shapes, styling references, and files, which is the actionable contract. All backend logic and tests are given as complete code.

**Type consistency:** `RecipeService(repository, locations, sales, forecasts)` constructor is fixed in Task 1 and reused unchanged in Tasks 2–3. `explode(points, recipes_by_item)` signature and its dataclasses are defined in Task 3 Step 3 and consumed by the same task's service method and tests. Frontend `useSaveRecipe` payload (`ingredient_id`/`ingredient_name`+`unit`/`amount` as string) matches the backend `RecipeLineInput` schema. `IngredientDemandResponse` fields (`generated_at`, `per_day`, `totals`, `coverage`) match between backend schema (Task 3 Step 5), router mapper (Step 8), and frontend consumer (Task 6).

**Note on the forecast engine dependency (Task 3):** the e2e test assumes the engine produces a 7-day forecast covering the sold items given ~4 same-weekday observations. If insufficient-history rules require more, extend the seed (more weeks / more weekdays) — do not weaken assertions. The explosion unit tests (Task 3 Steps 1–4) are independent of the engine and are the primary correctness guarantee.
