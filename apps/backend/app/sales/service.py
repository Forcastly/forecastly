"""Sales application logic.

Orchestrates CSV import (validate → persist import + upsert sales atomically) and
historical-sales retrieval. Location access is delegated to ``LocationService``
so the tenant boundary stays in one place. See ``docs/CSV_FORMAT.md`` and
``docs/DATA_MODEL.md`` §68.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.forecasts.exceptions import (
    InsufficientForecastHistoryError,
    StaleSalesDataError,
)
from app.forecasts.service import ForecastService
from app.locations.service import LocationService
from app.sales.csv import CsvValidationError, normalize_item_name, parse_sales_csv
from app.sales.exceptions import (
    DuplicateSalesImportError,
    InvalidSalesCursorError,
    SalesImportValidationError,
)
from app.sales.models import IMPORT_COMPLETED, IMPORT_FAILED, Sale, SalesImport
from app.sales.repository import (
    SalesCursor,
    SalesImportRepository,
    SalesRepository,
)
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def encode_cursor(cursor: SalesCursor) -> str:
    business_date, item_name, sale_id = cursor
    payload = json.dumps({"d": business_date.isoformat(), "n": item_name, "i": str(sale_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> SalesCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return date.fromisoformat(payload["d"]), payload["n"], UUID(payload["i"])
    except (ValueError, KeyError, binascii.Error) as exc:
        raise InvalidSalesCursorError() from exc


class SalesService:
    def __init__(
        self,
        sales: SalesRepository,
        imports: SalesImportRepository,
        locations: LocationService,
        forecasts: ForecastService,
    ) -> None:
        self.sales = sales
        self.imports = imports
        self.locations = locations
        self.forecasts = forecasts

    async def import_csv(
        self,
        *,
        user: User,
        location_id: UUID,
        filename: str,
        content: bytes,
    ) -> tuple[SalesImport, bool]:
        location = await self.locations.get(user, location_id)  # 404 if inaccessible
        content_hash = hashlib.sha256(content).hexdigest()

        if await self.imports.exists_content_hash(location.id, content_hash):
            raise DuplicateSalesImportError()

        try:
            rows = parse_sales_csv(content)
        except CsvValidationError as exc:
            await self._record_failed(location.id, filename, exc)
            raise SalesImportValidationError(
                details=[error.as_dict() for error in exc.errors]
            ) from exc

        try:
            sales_import = await self.imports.create(
                location_id=location.id,
                original_filename=filename,
                status=IMPORT_COMPLETED,
                content_hash=content_hash,
                row_count=len(rows),
                accepted_row_count=len(rows),
                rejected_row_count=0,
                completed_at=_now(),
            )
            await self.sales.upsert_many(
                location_id=location.id,
                sales_import_id=sales_import.id,
                rows=rows,
            )
            await self.imports.session.commit()
        except IntegrityError as exc:
            # Concurrent identical upload won the unique(content_hash) race.
            await self.imports.session.rollback()
            raise DuplicateSalesImportError() from exc

        await self.imports.session.refresh(sales_import)

        # Regenerate the forecast from the new data. The stale-data rule is a
        # customer-facing guard on manual generation, not on auto-run, so it is
        # disabled here; insufficient history simply yields no forecast.
        forecast_generated = False
        try:
            await self.forecasts.generate(
                user=user,
                location_id=location.id,
                enforce_stale=False,
            )
            forecast_generated = True
        except InsufficientForecastHistoryError, StaleSalesDataError:
            forecast_generated = False

        return sales_import, forecast_generated

    async def _record_failed(
        self,
        location_id: UUID,
        filename: str,
        exc: CsvValidationError,
    ) -> None:
        first = exc.errors[0]
        summary = (
            f"{len(exc.errors)} invalid row(s); "
            f"first: row {first.row} {first.field}: {first.message}"
        )
        # content_hash left NULL so a corrected re-upload is not treated as a
        # duplicate of the failed attempt.
        await self.imports.create(
            location_id=location_id,
            original_filename=filename,
            status=IMPORT_FAILED,
            accepted_row_count=0,
            error_message=summary,
            completed_at=_now(),
        )
        await self.imports.session.commit()

    async def list_imports(
        self,
        user: User,
        location_id: UUID,
        limit: int,
    ) -> list[SalesImport]:
        location = await self.locations.get(user, location_id)
        return await self.imports.list_for_location(location.id, limit)

    async def list_sales(
        self,
        *,
        user: User,
        location_id: UUID,
        start_date: date | None,
        end_date: date | None,
        item: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Sale], str | None]:
        location = await self.locations.get(user, location_id)
        decoded = decode_cursor(cursor) if cursor else None
        item_normalized = normalize_item_name(item) if item else None

        rows, next_cursor = await self.sales.list_for_location(
            location_id=location.id,
            start_date=start_date,
            end_date=end_date,
            item_normalized=item_normalized,
            limit=limit,
            cursor=decoded,
        )
        return rows, (encode_cursor(next_cursor) if next_cursor else None)

    async def summary(
        self,
        *,
        user: User,
        location_id: UUID,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[int, Decimal | None, int]:
        location = await self.locations.get(user, location_id)
        return await self.sales.summary(
            location_id=location.id, start_date=start_date, end_date=end_date
        )

    async def daily_totals(
        self,
        *,
        user: User,
        location_id: UUID,
        start_date: date | None,
        end_date: date | None,
    ) -> list[tuple[date, int, Decimal | None]]:
        location = await self.locations.get(user, location_id)
        return await self.sales.daily_totals(
            location_id=location.id, start_date=start_date, end_date=end_date
        )
