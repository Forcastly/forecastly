"""Location domain exceptions."""

from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError


class LocationNotFoundError(NotFoundError):
    code = "location_not_found"
    message = "The requested location was not found."


class LocationDuplicateNameError(ConflictError):
    code = "duplicate_location_name"
    message = "A location with this name already exists for this restaurant."
