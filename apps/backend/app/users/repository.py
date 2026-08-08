"""User persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User, UserIdentity


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_identity(self, provider: str, subject: str) -> User | None:
        stmt = (
            select(User)
            .join(UserIdentity)
            .where(
                UserIdentity.provider == provider,
                UserIdentity.provider_subject == subject,
            )
        )
        return await self.session.scalar(stmt)

    async def create_with_identity(
        self,
        *,
        email: str,
        provider: str,
        subject: str,
    ) -> User:
        user = User(email=email)
        user.identities.append(UserIdentity(provider=provider, provider_subject=subject))
        self.session.add(user)
        await self.session.flush()
        return user
