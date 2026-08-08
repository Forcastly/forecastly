"""Provider-neutral authenticated identity.

``AuthenticatedIdentity`` represents *who* made the request, as asserted by an
external identity provider (e.g. Clerk). It is deliberately decoupled from
Forecastly's internal ``User``: mapping an identity to a Forecastly user (and
authorization) belongs to the domain layer, not here. See
``docs/ARCHITECTURE.md`` §35–37.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    provider: str
    subject: str
    email: str | None = None
