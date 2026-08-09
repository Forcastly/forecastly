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
