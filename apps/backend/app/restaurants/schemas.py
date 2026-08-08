"""Restaurant API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.restaurants.models import Restaurant

Role = Literal["owner", "member"]


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name must not be empty.")
        return stripped


class RestaurantResponse(BaseModel):
    id: UUID
    name: str
    role: Role
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, restaurant: Restaurant, role: str) -> RestaurantResponse:
        return cls(
            id=restaurant.id,
            name=restaurant.name,
            role=role,  # type: ignore[arg-type]
            created_at=restaurant.created_at,
            updated_at=restaurant.updated_at,
        )


class RestaurantListResponse(BaseModel):
    items: list[RestaurantResponse]
