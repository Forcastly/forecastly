"""Recipe API schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.sales.csv import normalize_item_name


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


def _check_no_duplicate_ingredient_lines(lines: list[RecipeLineInput]) -> None:
    """Reject lines that reference the same ingredient twice — by id, or by
    name once normalized. A true duplicate here would otherwise trip the
    ``recipe_ingredients`` unique constraint and surface as a misleading
    "duplicate recipe" conflict; this catches it earlier with a clear error.
    """
    seen_ids: set[UUID] = set()
    seen_names: set[str] = set()
    for line in lines:
        if line.ingredient_id is not None:
            if line.ingredient_id in seen_ids:
                raise ValueError("Duplicate ingredient_id in lines.")
            seen_ids.add(line.ingredient_id)
        elif line.ingredient_name is not None:
            normalized = normalize_item_name(line.ingredient_name)
            if normalized in seen_names:
                raise ValueError("Duplicate ingredient_name in lines.")
            seen_names.add(normalized)


class RecipeCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    lines: list[RecipeLineInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_duplicate_ingredient_lines(self) -> RecipeCreate:
        _check_no_duplicate_ingredient_lines(self.lines)
        return self


class RecipeUpdate(BaseModel):
    lines: list[RecipeLineInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_duplicate_ingredient_lines(self) -> RecipeUpdate:
        _check_no_duplicate_ingredient_lines(self.lines)
        return self


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
