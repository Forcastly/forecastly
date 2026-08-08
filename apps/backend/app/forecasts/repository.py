"""Forecast persistence."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasts.models import Forecast, ForecastRun


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

    async def list_forecasts_for_run(self, run_id: UUID) -> list[Forecast]:
        stmt = (
            select(Forecast)
            .where(Forecast.forecast_run_id == run_id)
            .order_by(Forecast.forecast_date.asc(), Forecast.item_name.asc())
        )
        return list(await self.session.scalars(stmt))
