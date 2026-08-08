"""Forecast application logic.

Coordinates: authorize location → load per-item history from sales → run the
engine → persist a run and its points atomically. The engine owns the math; this
service owns orchestration and persistence. See ``docs/FORECASTING.md`` §17–29.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasts.engine import HORIZON_DAYS, ForecastEngine, HistoricalObservation
from app.forecasts.exceptions import (
    ForecastNotFoundError,
    InsufficientForecastHistoryError,
    InvalidForecastCursorError,
    StaleSalesDataError,
)
from app.forecasts.metrics import AccuracyMetrics, ForecastActualPair, compute_metrics
from app.forecasts.models import Forecast, ForecastRun
from app.forecasts.repository import ForecastRepository, ForecastRunCursor
from app.locations.exceptions import LocationNotFoundError
from app.locations.models import Location
from app.locations.service import LocationService
from app.sales.csv import normalize_item_name
from app.sales.repository import SalesRepository
from app.users.models import User

STALE_AFTER_DAYS = 7


def _now() -> datetime:
    return datetime.now(UTC)


def encode_run_cursor(cursor: ForecastRunCursor) -> str:
    generated_at, run_id = cursor
    payload = json.dumps({"g": generated_at.isoformat(), "i": str(run_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_run_cursor(cursor: str) -> ForecastRunCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(payload["g"]), UUID(payload["i"])
    except (ValueError, KeyError, binascii.Error) as exc:
        raise InvalidForecastCursorError() from exc


class ForecastService:
    def __init__(
        self,
        repository: ForecastRepository,
        sales: SalesRepository,
        locations: LocationService,
        engine: ForecastEngine | None = None,
    ) -> None:
        self.repository = repository
        self.sales = sales
        self.locations = locations
        self.engine = engine or ForecastEngine()

    @property
    def session(self) -> AsyncSession:
        return self.repository.session

    async def generate(
        self,
        *,
        user: User,
        location_id: UUID,
        as_of: date | None = None,
        enforce_stale: bool = True,
    ) -> tuple[ForecastRun, list[Forecast]]:
        location = await self.locations.get(user, location_id)  # 404 if inaccessible
        observations = await self.sales.list_observations(location.id)
        if not observations:
            raise InsufficientForecastHistoryError()

        history_by_item: dict[str, list[HistoricalObservation]] = defaultdict(list)
        display_name: dict[str, str] = {}
        for obs in observations:  # ordered oldest-first: last display value wins
            history_by_item[obs.item_name_normalized].append(
                HistoricalObservation(obs.business_date, obs.quantity)
            )
            display_name[obs.item_name_normalized] = obs.item_name

        history_start = min(o.business_date for o in observations)
        history_end = max(o.business_date for o in observations)

        if enforce_stale:
            today = as_of or self._local_today(location)
            if (today - history_end).days > STALE_AFTER_DAYS:
                raise StaleSalesDataError()

        forecast_start = history_end + timedelta(days=1)

        run = await self.repository.create_run(
            location_id=location.id,
            model_version=self.engine.model_version,
            history_start_date=history_start,
            history_end_date=history_end,
            horizon_days=HORIZON_DAYS,
            generated_at=_now(),
        )

        forecasts: list[Forecast] = []
        for normalized, history in history_by_item.items():
            for point in self.engine.generate(history, forecast_start, HORIZON_DAYS):
                forecasts.append(
                    Forecast(
                        forecast_run_id=run.id,
                        location_id=location.id,
                        forecast_date=point.forecast_date,
                        item_name=display_name[normalized],
                        item_name_normalized=normalized,
                        predicted_quantity=point.predicted_quantity,
                    )
                )

        if not forecasts:
            raise InsufficientForecastHistoryError()

        await self.repository.add_forecasts(forecasts)
        await self.session.commit()
        await self.session.refresh(run)
        return run, forecasts

    async def get_latest(
        self,
        user: User,
        location_id: UUID,
    ) -> tuple[ForecastRun, list[Forecast]]:
        location = await self.locations.get(user, location_id)
        run = await self.repository.latest_run(location.id)
        if run is None:
            raise ForecastNotFoundError()
        forecasts = await self.repository.list_forecasts_for_run(run.id)
        return run, forecasts

    async def list_runs(
        self,
        *,
        user: User,
        location_id: UUID,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[ForecastRun], str | None]:
        location = await self.locations.get(user, location_id)
        decoded = decode_run_cursor(cursor) if cursor else None
        runs, next_cursor = await self.repository.list_runs(
            location_id=location.id, limit=limit, cursor=decoded
        )
        return runs, (encode_run_cursor(next_cursor) if next_cursor else None)

    async def get_run(
        self,
        *,
        user: User,
        forecast_run_id: UUID,
    ) -> tuple[ForecastRun, list[Forecast]]:
        run = await self.repository.get_run(forecast_run_id)
        if run is None:
            raise ForecastNotFoundError()
        # Authorize via the owning location; hide inaccessible runs as not-found.
        try:
            await self.locations.get(user, run.location_id)
        except LocationNotFoundError as exc:
            raise ForecastNotFoundError() from exc
        forecasts = await self.repository.list_forecasts_for_run(run.id)
        return run, forecasts

    async def accuracy(
        self,
        *,
        user: User,
        location_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        item: str | None = None,
        forecast_run_id: UUID | None = None,
    ) -> AccuracyMetrics:
        location = await self.locations.get(user, location_id)
        item_normalized = normalize_item_name(item) if item else None
        pairs = await self.repository.forecast_actual_pairs(
            location_id=location.id,
            start_date=start_date,
            end_date=end_date,
            item_normalized=item_normalized,
            forecast_run_id=forecast_run_id,
        )
        return compute_metrics(
            [
                ForecastActualPair(predicted=predicted, actual=Decimal(actual))
                for predicted, actual in pairs
            ]
        )

    @staticmethod
    def _local_today(location: Location) -> date:
        return datetime.now(ZoneInfo(location.timezone)).date()
