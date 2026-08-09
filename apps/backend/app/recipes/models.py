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

    recipe: Mapped[Recipe] = relationship(back_populates="lines", lazy="joined")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
