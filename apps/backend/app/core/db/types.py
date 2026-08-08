"""Reusable, domain-agnostic persistence types and mixins.

These are generic building blocks (UUID primary keys, timestamp columns) usable
by any FastAPI application — hence they live in ``core``. Domain semantics do
not belong here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def new_uuid() -> uuid.UUID:
    """Generate an application-owned UUID.

    Prefers UUIDv7 (time-sortable, better index locality) when the runtime
    provides it (Python 3.14+), falling back to UUIDv4. Forecastly always
    generates its own identifiers — see ``docs/DATA_MODEL.md``.
    """

    uuid7 = getattr(uuid, "uuid7", None)
    if uuid7 is not None:
        return uuid7()
    return uuid.uuid4()


# Annotated column declarations (SQLAlchemy 2.0 style). Use as:
#     id: Mapped[UUIDPrimaryKey]
#     created_at: Mapped[CreatedAt]
UUIDPrimaryKey = Annotated[
    uuid.UUID,
    mapped_column(primary_key=True, default=new_uuid),
]

CreatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False),
]

UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
]


class TimestampMixin:
    """Adds timezone-aware ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
