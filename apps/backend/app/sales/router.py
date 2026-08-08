"""Sales HTTP routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.dependencies import SessionDep, SettingsDep
from app.locations.repository import LocationRepository
from app.locations.service import LocationService
from app.restaurants.repository import RestaurantRepository
from app.sales.exceptions import SalesFileTooLargeError, UnsupportedSalesFileError
from app.sales.repository import SalesImportRepository, SalesRepository
from app.sales.schemas import (
    SaleResponse,
    SalesImportListItem,
    SalesImportListResponse,
    SalesImportResponse,
    SalesListResponse,
)
from app.sales.service import SalesService
from app.users.dependencies import CurrentUser

router = APIRouter(tags=["sales"])


def get_sales_service(session: SessionDep) -> SalesService:
    locations = LocationService(LocationRepository(session), RestaurantRepository(session))
    return SalesService(SalesRepository(session), SalesImportRepository(session), locations)


SalesServiceDep = Annotated[SalesService, Depends(get_sales_service)]


@router.post(
    "/locations/{location_id}/sales/imports",
    status_code=status.HTTP_201_CREATED,
    response_model=SalesImportResponse,
)
async def upload_sales_csv(
    location_id: UUID,
    user: CurrentUser,
    service: SalesServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
) -> SalesImportResponse:
    if not (file.filename or "").lower().endswith(".csv"):
        raise UnsupportedSalesFileError()

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise SalesFileTooLargeError()

    sales_import = await service.import_csv(
        user=user,
        location_id=location_id,
        filename=file.filename or "upload.csv",
        content=content,
    )
    # Forecast auto-generation is wired once the forecasts domain exists.
    return SalesImportResponse.from_entity(sales_import, forecast_generated=False)


@router.get(
    "/locations/{location_id}/sales/imports",
    response_model=SalesImportListResponse,
)
async def list_sales_imports(
    location_id: UUID,
    user: CurrentUser,
    service: SalesServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SalesImportListResponse:
    imports = await service.list_imports(user, location_id, limit)
    return SalesImportListResponse(items=[SalesImportListItem.model_validate(i) for i in imports])


@router.get("/locations/{location_id}/sales", response_model=SalesListResponse)
async def list_sales(
    location_id: UUID,
    user: CurrentUser,
    service: SalesServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    item: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    cursor: Annotated[str | None, Query()] = None,
) -> SalesListResponse:
    rows, next_cursor = await service.list_sales(
        user=user,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
        item=item,
        limit=limit,
        cursor=cursor,
    )
    return SalesListResponse(
        items=[SaleResponse.model_validate(row) for row in rows],
        next_cursor=next_cursor,
    )
