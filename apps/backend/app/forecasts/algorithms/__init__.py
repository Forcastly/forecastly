"""Candidate forecasting models for the tournament."""

from app.forecasts.algorithms.base import (
    SEASONAL_PERIOD_DAYS,
    ForecastModel,
    quantize,
    same_weekday_history,
    seasonal_reference,
)
from app.forecasts.algorithms.ewma_weekday import EwmaWeekdayModel
from app.forecasts.algorithms.holt_winters import HoltWintersModel
from app.forecasts.algorithms.level_adjusted_seasonal_naive import (
    LevelAdjustedSeasonalNaiveModel,
    LevelAdjustedSeasonalNaiveV2Model,
    level_ratio,
)
from app.forecasts.algorithms.seasonal_average import SeasonalAverageModel
from app.forecasts.algorithms.seasonal_naive import SeasonalNaiveModel

__all__ = [
    "SEASONAL_PERIOD_DAYS",
    "EwmaWeekdayModel",
    "ForecastModel",
    "HoltWintersModel",
    "LevelAdjustedSeasonalNaiveModel",
    "LevelAdjustedSeasonalNaiveV2Model",
    "SeasonalAverageModel",
    "SeasonalNaiveModel",
    "level_ratio",
    "quantize",
    "same_weekday_history",
    "seasonal_reference",
]
