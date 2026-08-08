"""Async session factory and request-scoped session dependency.

A session lives for one operation / HTTP request. Repositories receive this
session; they do not create their own. Transaction boundaries (``commit``) are
owned by the service layer — this dependency only rolls back on error and
guarantees the session is closed. See ``docs/ARCHITECTURE.md`` §30–32.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.engine import engine

session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
