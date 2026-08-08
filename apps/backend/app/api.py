"""API assembly.

Aggregates domain routers under the ``/api`` prefix. Domain routers are added
here as each domain is implemented — this file contains no business logic.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

# Domain routers are wired in as they are implemented, e.g.:
#   from app.restaurants.router import router as restaurants_router
#   api_router.include_router(restaurants_router)
