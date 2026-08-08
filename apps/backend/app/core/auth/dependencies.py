"""FastAPI authentication dependencies.

Resolves the current :class:`AuthenticatedIdentity` for a request. In
development, a stub identity is trusted so the API is usable before Clerk is
wired. This fallback is hard-disabled in production.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from app.core.auth.clerk import ClerkVerifier
from app.core.auth.identity import AuthenticatedIdentity
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError

DEV_PROVIDER = "dev"


async def get_current_identity(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_dev_subject: Annotated[str | None, Header()] = None,
) -> AuthenticatedIdentity:
    # Development fallback: trust a stub identity. Never active in production.
    if settings.dev_auth_enabled and not settings.is_production:
        return AuthenticatedIdentity(
            provider=DEV_PROVIDER,
            subject=x_dev_subject or settings.dev_auth_subject,
            email=settings.dev_auth_email,
        )

    if not settings.clerk_secret_key:
        raise AuthenticationError("Authentication provider is not configured.")

    verifier = ClerkVerifier(settings.clerk_secret_key)
    return await verifier.verify(_bearer_token(authorization))


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    return authorization[len("bearer ") :].strip()


CurrentIdentity = Annotated[AuthenticatedIdentity, Depends(get_current_identity)]
