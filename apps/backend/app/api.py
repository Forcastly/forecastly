"""API assembly.

Aggregates domain routers under the ``/api`` prefix. Domain routers are added
here as each domain is implemented — this file contains no business logic.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.forecasts.router import router as forecasts_router
from app.locations.router import router as locations_router
from app.recipes.router import router as recipes_router
from app.restaurants.router import router as restaurants_router
from app.sales.router import router as sales_router
from app.users.router import router as users_router

api_router = APIRouter(prefix="/api")

api_router.include_router(users_router)
api_router.include_router(restaurants_router)
api_router.include_router(locations_router)
api_router.include_router(sales_router)
api_router.include_router(forecasts_router)
api_router.include_router(recipes_router)
