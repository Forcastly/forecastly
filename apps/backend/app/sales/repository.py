"""Sales and sales-import persistence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.types import new_uuid
from app.sales.csv import ParsedSaleRow
from app.sales.models import Sale, SalesImport

# Cursor for keyset pagination: the last row's (business_date, item_name, id).
SalesCursor = tuple[date, str, UUID]


class SalesImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists_content_hash(self, location_id: UUID, content_hash: str) -> bool:
        stmt = (
            select(SalesImport.id)
            .where(
                SalesImport.location_id == location_id,
                SalesImport.content_hash == content_hash,
            )
            .limit(1)
        )
        return await self.session.scalar(stmt) is not None

    async def create(
        self,
        *,
        location_id: UUID,
        original_filename: str,
        status: str,
        content_hash: str | None = None,
        row_count: int | None = None,
        accepted_row_count: int | None = None,
        rejected_row_count: int | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
    ) -> SalesImport:
        sales_import = SalesImport(
            location_id=location_id,
            original_filename=original_filename,
            status=status,
            content_hash=content_hash,
            row_count=row_count,
            accepted_row_count=accepted_row_count,
            rejected_row_count=rejected_row_count,
            error_message=error_message,
            completed_at=completed_at,
        )
        self.session.add(sales_import)
        await self.session.flush()
        return sales_import

    async def list_for_location(self, location_id: UUID, limit: int) -> list[SalesImport]:
        stmt = (
            select(SalesImport)
            .where(SalesImport.location_id == location_id)
            .order_by(SalesImport.created_at.desc())
            .limit(limit)
        )
        return list(await self.session.scalars(stmt))


class SalesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(
        self,
        *,
        location_id: UUID,
        sales_import_id: UUID,
        rows: list[ParsedSaleRow],
    ) -> int:
        """Insert rows, updating any existing observation for the same
        (location, business_date, normalized item). Returns the row count."""
        if not rows:
            return 0

        values = [
            {
                "id": new_uuid(),
                "location_id": location_id,
                "sales_import_id": sales_import_id,
                "business_date": row.business_date,
                "item_name": row.item_name,
                "item_name_normalized": row.item_name_normalized,
                "quantity": row.quantity,
                "revenue": row.revenue,
            }
            for row in rows
        ]
        stmt = pg_insert(Sale).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["location_id", "business_date", "item_name_normalized"],
            set_={
                "quantity": stmt.excluded.quantity,
                "revenue": stmt.excluded.revenue,
                "item_name": stmt.excluded.item_name,
                "sales_import_id": stmt.excluded.sales_import_id,
                "updated_at": func.now(),
            },
        )
        await self.session.execute(stmt)
        return len(rows)

    async def list_for_location(
        self,
        *,
        location_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        item_normalized: str | None = None,
        limit: int = 100,
        cursor: SalesCursor | None = None,
    ) -> tuple[list[Sale], SalesCursor | None]:
        stmt = select(Sale).where(Sale.location_id == location_id)
        if start_date is not None:
            stmt = stmt.where(Sale.business_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Sale.business_date <= end_date)
        if item_normalized is not None:
            stmt = stmt.where(Sale.item_name_normalized == item_normalized)
        if cursor is not None:
            bd, name, sale_id = cursor
            # Keyset for ORDER BY business_date DESC, item_name ASC, id ASC.
            stmt = stmt.where(
                or_(
                    Sale.business_date < bd,
                    and_(Sale.business_date == bd, Sale.item_name > name),
                    and_(
                        Sale.business_date == bd,
                        Sale.item_name == name,
                        Sale.id > sale_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            Sale.business_date.desc(),
            Sale.item_name.asc(),
            Sale.id.asc(),
        ).limit(limit + 1)

        found = list(await self.session.scalars(stmt))
        has_more = len(found) > limit
        page = found[:limit]
        next_cursor: SalesCursor | None = None
        if has_more and page:
            last = page[-1]
            next_cursor = (last.business_date, last.item_name, last.id)
        return page, next_cursor

    async def list_observations(self, location_id: UUID) -> list[Sale]:
        """All sales for a location, oldest first — history for forecasting."""
        stmt = (
            select(Sale).where(Sale.location_id == location_id).order_by(Sale.business_date.asc())
        )
        return list(await self.session.scalars(stmt))

    async def summary(
        self,
        *,
        location_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[int, Decimal | None, int]:
        """Aggregate (total_quantity, total_revenue, days_with_data) for a range.

        ``total_revenue`` is None when no revenue is recorded — sums ignore NULL
        revenue rather than treating missing revenue as zero.
        """
        stmt = select(
            func.coalesce(func.sum(Sale.quantity), 0),
            func.sum(Sale.revenue),
            func.count(func.distinct(Sale.business_date)),
        ).where(Sale.location_id == location_id)
        if start_date is not None:
            stmt = stmt.where(Sale.business_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Sale.business_date <= end_date)

        total_quantity, total_revenue, days_with_data = (await self.session.execute(stmt)).one()
        return int(total_quantity), total_revenue, int(days_with_data)

    async def daily_totals(
        self,
        *,
        location_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[tuple[date, int, Decimal | None]]:
        """Per-day totals (quantity, revenue) summed across all items, oldest
        first. Revenue is None for a day when no row that day recorded revenue —
        missing revenue is not treated as zero.
        """
        stmt = select(
            Sale.business_date,
            func.coalesce(func.sum(Sale.quantity), 0),
            func.sum(Sale.revenue),
        ).where(Sale.location_id == location_id)
        if start_date is not None:
            stmt = stmt.where(Sale.business_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Sale.business_date <= end_date)
        stmt = stmt.group_by(Sale.business_date).order_by(Sale.business_date.asc())

        rows = (await self.session.execute(stmt)).all()
        return [(day, int(quantity), revenue) for day, quantity, revenue in rows]

    async def average_unit_prices(self, location_id: UUID) -> dict[str, Decimal]:
        """Average unit price (sum revenue / sum quantity) per normalized item,
        over the rows that recorded revenue. Used to turn predicted quantities
        into estimated revenue. Items that never recorded revenue are omitted.
        """
        stmt = (
            select(
                Sale.item_name_normalized,
                func.sum(Sale.revenue),
                func.sum(Sale.quantity),
            )
            .where(Sale.location_id == location_id, Sale.revenue.is_not(None))
            .group_by(Sale.item_name_normalized)
        )
        prices: dict[str, Decimal] = {}
        for name, revenue, quantity in (await self.session.execute(stmt)).all():
            if revenue is not None and quantity:
                prices[name] = Decimal(revenue) / Decimal(quantity)
        return prices
