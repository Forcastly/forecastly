"""Current-user dependency.

Resolves the authenticated identity to a Forecastly ``User``. Other domains
depend on this for authorization.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.auth.dependencies import CurrentIdentity
from app.core.dependencies import SessionDep
from app.users.models import User
from app.users.repository import UserRepository
from app.users.service import UserService


async def get_current_user(identity: CurrentIdentity, session: SessionDep) -> User:
    service = UserService(UserRepository(session))
    return await service.resolve_user(identity)


CurrentUser = Annotated[User, Depends(get_current_user)]
