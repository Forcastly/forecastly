"""Test fixtures.

Tests run against a real PostgreSQL database (``forecastly_test``) so PG-specific
behavior — UUIDs, constraints, upserts — is exercised for real, per
``docs/ARCHITECTURE.md`` §54. Each test gets a clean schema via truncation and a
session bound to the test database through a dependency override.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register all models on Base.metadata before create_all.
import app.forecasts.models  # noqa: F401
import app.locations.models  # noqa: F401
import app.restaurants.models  # noqa: F401
import app.sales.models  # noqa: F401
import app.users.models  # noqa: F401
from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.session import get_session
from app.main import app

TEST_DB_NAME = "forecastly_test"
# Child-before-parent order for TRUNCATE readability (CASCADE handles FKs anyway).
_TABLES = (
    "forecasts",
    "forecast_runs",
    "sales",
    "sales_imports",
    "locations",
    "restaurant_memberships",
    "restaurants",
    "user_identities",
    "users",
)


def _urls() -> tuple[str, str]:
    """Return ``(async_test_url, sync_admin_dsn)`` derived from settings."""
    raw = get_settings().database_url  # postgresql+psycopg://.../forecastly
    prefix, _, _name = raw.rpartition("/")
    async_test_url = f"{prefix}/{TEST_DB_NAME}"
    admin_dsn = prefix.replace("postgresql+psycopg://", "postgresql://") + "/postgres"
    return async_test_url, admin_dsn


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    async_test_url, admin_dsn = _urls()

    # Create the test database if absent (CREATE DATABASE needs autocommit).
    admin = psycopg.connect(admin_dsn, autocommit=True)
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        admin.close()

    # Build a fresh schema with a synchronous engine (no event-loop concerns).
    sync_engine = create_engine(async_test_url)
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()


@pytest_asyncio.fixture
async def client(_test_database: None) -> AsyncGenerator[AsyncClient]:
    async_test_url, _ = _urls()
    engine = create_async_engine(async_test_url)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_session() -> AsyncGenerator:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))
        await engine.dispose()
