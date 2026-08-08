"""User HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.users.dependencies import CurrentUser
from app.users.schemas import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
