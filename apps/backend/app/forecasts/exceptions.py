"""Forecast domain exceptions."""

from __future__ import annotations

from app.core.exceptions import ForecastlyError, NotFoundError, ValidationError


class ForecastNotFoundError(NotFoundError):
    code = "forecast_not_found"
    message = "No forecast has been generated for this location."


class ModelEvaluationNotFoundError(NotFoundError):
    code = "model_evaluation_not_found"
    message = "No model evaluation has been run for this location."


class InvalidForecastCursorError(ValidationError):
    code = "invalid_cursor"
    message = "The pagination cursor is invalid."


class InsufficientForecastHistoryError(ForecastlyError):
    code = "insufficient_forecast_history"
    status_code = 422
    message = "This location does not have enough historical sales data to forecast."


class StaleSalesDataError(ForecastlyError):
    code = "stale_sales_data"
    status_code = 422
    message = "Sales data is out of date; upload newer sales before forecasting."
