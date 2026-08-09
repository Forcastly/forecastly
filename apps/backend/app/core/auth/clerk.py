"""Clerk integration boundary.

All Clerk-specific behavior stays in this module so the rest of the application
remains provider-neutral. Verification uses the official ``clerk-backend-api``
networkless JWT helper: given a Clerk session token and the instance
``CLERK_SECRET_KEY``, it validates the signature (against Clerk's JWKS, fetched
and cached by the SDK), issuer, and expiry, and returns the token claims.
"""

from __future__ import annotations

import asyncio

from clerk_backend_api.security.types import TokenVerificationError, VerifyTokenOptions
from clerk_backend_api.security.verifytoken import verify_token

from app.core.auth.identity import AuthenticatedIdentity
from app.core.exceptions import AuthenticationError

PROVIDER = "clerk"


class ClerkVerifier:
    """Verifies a Clerk session token and returns a neutral identity."""

    def __init__(
        self,
        secret_key: str,
        authorized_parties: list[str] | None = None,
    ) -> None:
        self._options = VerifyTokenOptions(
            secret_key=secret_key,
            # Guards against token replay from other origins. Optional: when
            # empty, only signature/issuer/expiry are enforced.
            authorized_parties=authorized_parties or None,
        )

    async def verify(self, token: str) -> AuthenticatedIdentity:
        try:
            # verify_token is synchronous and performs (cached) network I/O for
            # the JWKS, so run it off the event loop.
            claims = await asyncio.to_thread(verify_token, token, self._options)
        except TokenVerificationError as exc:
            raise AuthenticationError("Invalid or expired session token.") from exc

        subject = claims.get("sub")
        if not subject:
            raise AuthenticationError("Session token is missing a subject.")

        email = claims.get("email")
        return AuthenticatedIdentity(
            provider=PROVIDER,
            subject=str(subject),
            email=email if isinstance(email, str) else None,
        )
