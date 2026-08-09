"""Sales API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.sales.models import SalesImport


class SalesImportResponse(BaseModel):
    id: UUID
    location_id: UUID
    original_filename: str
    status: str
    row_count: int | None
    accepted_row_count: int | None
    rejected_row_count: int | None
    created_at: datetime
    completed_at: datetime | None
    forecast_generated: bool

    @classmethod
    def from_entity(
        cls,
        sales_import: SalesImport,
        *,
        forecast_generated: bool,
    ) -> SalesImportResponse:
        return cls(
            id=sales_import.id,
            location_id=sales_import.location_id,
            original_filename=sales_import.original_filename,
            status=sales_import.status,
            row_count=sales_import.row_count,
            accepted_row_count=sales_import.accepted_row_count,
            rejected_row_count=sales_import.rejected_row_count,
            created_at=sales_import.created_at,
            completed_at=sales_import.completed_at,
            forecast_generated=forecast_generated,
        )


class SalesImportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    status: str
    row_count: int | None
    accepted_row_count: int | None
    rejected_row_count: int | None
    created_at: datetime
    completed_at: datetime | None


class SalesImportListResponse(BaseModel):
    items: list[SalesImportListItem]


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_date: date
    item_name: str
    quantity: int
    revenue: Decimal | None


class SalesListResponse(BaseModel):
    items: list[SaleResponse]
    next_cursor: str | None


class SalesSummaryResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    total_quantity: int
    total_revenue: Decimal | None
    days_with_data: int


class SalesDailyPoint(BaseModel):
    business_date: date
    total_quantity: int
    total_revenue: Decimal | None


class SalesDailyResponse(BaseModel):
    items: list[SalesDailyPoint]
