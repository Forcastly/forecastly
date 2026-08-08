"""Restaurant domain exceptions."""

from __future__ import annotations

from app.core.exceptions import NotFoundError


class RestaurantNotFoundError(NotFoundError):
    code = "restaurant_not_found"
    message = "The requested restaurant was not found."
