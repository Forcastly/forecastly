"""Clerk integration boundary.

All Clerk-specific behavior stays in this module so the rest of the application
remains provider-neutral. This is a placeholder for the MVP shell: wire
``clerk-backend-api`` here once a ``CLERK_SECRET_KEY`` is configured.
"""

from __future__ import annotations

from app.core.auth.identity import AuthenticatedIdentity

PROVIDER = "clerk"


class ClerkVerifier:
    """Verifies a Clerk session token and returns a neutral identity."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    async def verify(self, token: str) -> AuthenticatedIdentity:
        # TODO: verify `token` with clerk-backend-api and map the result to
        # AuthenticatedIdentity(provider=PROVIDER, subject=<clerk user id>, ...).
        raise NotImplementedError(
            "Clerk verification is not wired yet. Implement ClerkVerifier.verify "
            "using clerk-backend-api once CLERK_SECRET_KEY is available."
        )
