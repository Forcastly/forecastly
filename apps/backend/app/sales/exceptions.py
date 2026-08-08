"""Sales domain exceptions (HTTP-mapped)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import ConflictError, ForecastlyError, ValidationError


class SalesImportValidationError(ForecastlyError):
    code = "invalid_sales_import"
    status_code = 422
    message = "The CSV could not be imported."

    def __init__(self, *, details: list[dict[str, Any]]) -> None:
        super().__init__(details=details)


class DuplicateSalesImportError(ConflictError):
    code = "duplicate_sales_import"
    message = "This file has already been imported for this location."


class SalesFileTooLargeError(ForecastlyError):
    code = "file_too_large"
    status_code = 413
    message = "The uploaded file exceeds the maximum allowed size."


class UnsupportedSalesFileError(ForecastlyError):
    code = "unsupported_file_type"
    status_code = 415
    message = "The upload must be a .csv file."


class InvalidSalesCursorError(ValidationError):
    code = "invalid_cursor"
    message = "The pagination cursor is invalid."
