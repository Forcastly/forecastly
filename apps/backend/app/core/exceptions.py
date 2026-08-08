"""Application error types and their HTTP representation.

Domain and service code should raise :class:`ForecastlyError` subclasses (or
domain-specific subclasses defined in each module's ``exceptions.py``). The HTTP
boundary translates them into the standard error envelope defined in
``docs/API_CONTRACT.md``:

    {"error": {"code": "...", "message": "...", "details": [...]}}

Business logic must not raise FastAPI ``HTTPException``.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ForecastlyError(Exception):
    """Base class for errors surfaced at the API boundary."""

    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        self.details = details


class NotFoundError(ForecastlyError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "The requested resource was not found."


class AuthenticationError(ForecastlyError):
    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication is required."


class PermissionDeniedError(ForecastlyError):
    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


class ConflictError(ForecastlyError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The operation conflicts with existing state."


class ValidationError(ForecastlyError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The request contains invalid fields."


def _error_body(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


async def _forecastly_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ForecastlyError)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "field": ".".join(str(part) for part in err["loc"] if part != "body"),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body(
            "validation_error",
            "The request contains invalid fields.",
            details,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ForecastlyError, _forecastly_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
