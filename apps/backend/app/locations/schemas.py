"""Location API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name must not be empty.")
        return stripped

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        stripped = value.strip()
        try:
            ZoneInfo(stripped)
        except ZoneInfoNotFoundError, ValueError:
            raise ValueError("Must be a valid IANA timezone identifier.") from None
        return stripped


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    name: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class LocationListResponse(BaseModel):
    items: list[LocationResponse]
