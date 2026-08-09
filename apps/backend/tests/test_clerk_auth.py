"""Clerk token verification and auth-dependency precedence."""

from __future__ import annotations

import pytest
from clerk_backend_api.security.types import (
    TokenVerificationError,
    TokenVerificationErrorReason,
)

from app.core.auth import clerk as clerk_module
from app.core.auth.clerk import ClerkVerifier
from app.core.auth.dependencies import DEV_PROVIDER, get_current_identity
from app.core.config import Settings
from app.core.exceptions import AuthenticationError


def _patch_verify(monkeypatch, result=None, *, raises: Exception | None = None) -> None:
    def fake_verify_token(token, options):
        _ = (token, options)
        if raises is not None:
            raise raises
        return result

    monkeypatch.setattr(clerk_module, "verify_token", fake_verify_token)


async def test_verify_maps_claims_to_identity(monkeypatch) -> None:
    _patch_verify(monkeypatch, {"sub": "user_abc123", "email": "chef@example.com"})
    identity = await ClerkVerifier("sk_test_x").verify("token")
    assert identity.provider == "clerk"
    assert identity.subject == "user_abc123"
    assert identity.email == "chef@example.com"


async def test_verify_without_email_is_allowed(monkeypatch) -> None:
    _patch_verify(monkeypatch, {"sub": "user_abc123"})
    identity = await ClerkVerifier("sk_test_x").verify("token")
    assert identity.subject == "user_abc123"
    assert identity.email is None


async def test_verify_rejects_invalid_token(monkeypatch) -> None:
    _patch_verify(
        monkeypatch,
        raises=TokenVerificationError(TokenVerificationErrorReason.TOKEN_INVALID),
    )
    with pytest.raises(AuthenticationError):
        await ClerkVerifier("sk_test_x").verify("bad")


async def test_verify_requires_subject(monkeypatch) -> None:
    _patch_verify(monkeypatch, {"email": "chef@example.com"})
    with pytest.raises(AuthenticationError):
        await ClerkVerifier("sk_test_x").verify("token")


async def test_dev_fallback_used_when_clerk_not_configured() -> None:
    settings = Settings(clerk_secret_key=None, dev_auth_enabled=True)
    identity = await get_current_identity(
        settings=settings, authorization=None, x_dev_subject="owner"
    )
    assert identity.provider == DEV_PROVIDER
    assert identity.subject == "owner"


async def test_clerk_used_when_configured_even_with_dev_enabled(monkeypatch) -> None:
    # Setting the secret key must take precedence over the dev fallback.
    _patch_verify(monkeypatch, {"sub": "user_from_clerk"})
    settings = Settings(clerk_secret_key="sk_test_x", dev_auth_enabled=True)
    identity = await get_current_identity(
        settings=settings,
        authorization="Bearer real.jwt.token",
        x_dev_subject="owner",
    )
    assert identity.provider == "clerk"
    assert identity.subject == "user_from_clerk"


async def test_missing_bearer_rejected_when_clerk_configured() -> None:
    settings = Settings(clerk_secret_key="sk_test_x", dev_auth_enabled=True)
    with pytest.raises(AuthenticationError):
        await get_current_identity(
            settings=settings, authorization=None, x_dev_subject="owner"
        )
