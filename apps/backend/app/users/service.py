"""User application logic.

Maps a provider-neutral :class:`AuthenticatedIdentity` to a Forecastly ``User``,
provisioning one on first sight (``docs/API_CONTRACT.md`` §14).
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.auth.identity import AuthenticatedIdentity
from app.users.models import User
from app.users.repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def resolve_user(self, identity: AuthenticatedIdentity) -> User:
        """Return the Forecastly user for an identity, creating it if needed."""

        user = await self.repository.get_by_identity(identity.provider, identity.subject)
        if user is not None:
            return user

        try:
            user = await self.repository.create_with_identity(
                email=identity.email or "",
                provider=identity.provider,
                subject=identity.subject,
            )
            await self.repository.session.commit()
        except IntegrityError:
            # Concurrent first-request created it first — fall back to the row.
            await self.repository.session.rollback()
            user = await self.repository.get_by_identity(identity.provider, identity.subject)
            if user is None:
                raise

        return user
