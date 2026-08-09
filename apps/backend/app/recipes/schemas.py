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
