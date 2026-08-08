"""Shared FastAPI dependencies.

Convenience ``Annotated`` aliases used across domain routers. Domain-specific
dependencies (repositories, services) live in their own modules.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
