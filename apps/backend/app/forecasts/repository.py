"""Forecast persistence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.forecasts.models import (
    Forecast,
    ForecastRun,
    ModelEvaluationResult,
    ModelEvaluationRun,
)
from app.sales.models import Sale

# Cursor for forecast-run pagination: the last run's (generated_at, id).
ForecastRunCursor = tuple[datetime, UUID]


class ForecastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        *,
        location_id: UUID,
        model_version: str,
        history_start_date: date | None,
        history_end_date: date | None,
        horizon_days: int,
        generated_at: datetime,
    ) -> ForecastRun:
        run = ForecastRun(
            location_id=location_id,
            model_version=model_version,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            horizon_days=horizon_days,
            generated_at=generated_at,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def add_forecasts(self, forecasts: list[Forecast]) -> None:
        self.session.add_all(forecasts)
        await self.session.flush()

    async def latest_run(self, location_id: UUID) -> ForecastRun | None:
        stmt = (
            select(ForecastRun)
            .where(ForecastRun.location_id == location_id)
            .order_by(ForecastRun.generated_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def get_run(self, run_id: UUID) -> ForecastRun | None:
        return await self.session.get(ForecastRun, run_id)

    async def list_runs(
        self,
        *,
        location_id: UUID,
        limit: int,
        cursor: ForecastRunCursor | None = None,
    ) -> tuple[list[ForecastRun], ForecastRunCursor | None]:
        stmt = select(ForecastRun).where(ForecastRun.location_id == location_id)
        if cursor is not None:
            generated_at, run_id = cursor
            # Keyset for ORDER BY generated_at DESC, id ASC.
            stmt = stmt.where(
                or_(
                    ForecastRun.generated_at < generated_at,
                    and_(
                        ForecastRun.generated_at == generated_at,
                        ForecastRun.id > run_id,
                    ),
                )
            )
        stmt = stmt.order_by(ForecastRun.generated_at.desc(), ForecastRun.id.asc()).limit(limit + 1)

        found = list(await self.session.scalars(stmt))
        has_more = len(found) > limit
        page = found[:limit]
        next_cursor: ForecastRunCursor | None = None
        if has_more and page:
            next_cursor = (page[-1].generated_at, page[-1].id)
        return page, next_cursor

    async def list_forecasts_for_run(self, run_id: UUID) -> list[Forecast]:
        stmt = (
            select(Forecast)
            .where(Forecast.forecast_run_id == run_id)
            .order_by(Forecast.forecast_date.asc(), Forecast.item_name.asc())
        )
        return list(await self.session.scalars(stmt))

    async def forecast_actual_pairs(
        self,
        *,
        location_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        item_normalized: str | None = None,
        forecast_run_id: UUID | None = None,
    ) -> list[tuple[Decimal, int]]:
        """Predicted vs actual pairs for evaluation.

        For each (forecast_date, item) the most recent run's prediction is used,
        joined to the actual sale for that date. Only dates with a known actual
        are returned, so missing actuals are excluded (not treated as zero).
        """
        predicted = (
            select(
                Forecast.forecast_date.label("forecast_date"),
                Forecast.item_name_normalized.label("item"),
                Forecast.predicted_quantity.label("predicted"),
            )
            .join(ForecastRun, Forecast.forecast_run_id == ForecastRun.id)
            .where(Forecast.location_id == location_id)
        )
        if start_date is not None:
            predicted = predicted.where(Forecast.forecast_date >= start_date)
        if end_date is not None:
            predicted = predicted.where(Forecast.forecast_date <= end_date)
        if item_normalized is not None:
            predicted = predicted.where(Forecast.item_name_normalized == item_normalized)
        if forecast_run_id is not None:
            predicted = predicted.where(ForecastRun.id == forecast_run_id)

        # DISTINCT ON keeps the newest prediction per (date, item).
        predicted = predicted.order_by(
            Forecast.forecast_date,
            Forecast.item_name_normalized,
            ForecastRun.generated_at.desc(),
        ).distinct(Forecast.forecast_date, Forecast.item_name_normalized)
        latest = predicted.subquery()

        stmt = select(latest.c.predicted, Sale.quantity).join(
            Sale,
            and_(
                Sale.location_id == location_id,
                Sale.business_date == latest.c.forecast_date,
                Sale.item_name_normalized == latest.c.item,
            ),
        )
        result = await self.session.execute(stmt)
        return [(row.predicted, row.quantity) for row in result]


class ModelEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, run: ModelEvaluationRun) -> ModelEvaluationRun:
        """Persist a run and its cascaded results/windows."""
        self.session.add(run)
        await self.session.flush()
        return run

    async def latest(self, location_id: UUID) -> ModelEvaluationRun | None:
        stmt = (
            select(ModelEvaluationRun)
            .where(ModelEvaluationRun.location_id == location_id)
            .order_by(ModelEvaluationRun.generated_at.desc())
            .limit(1)
            .options(
                selectinload(ModelEvaluationRun.evaluations).selectinload(
                    ModelEvaluationResult.windows
                )
            )
        )
        return await self.session.scalar(stmt)
