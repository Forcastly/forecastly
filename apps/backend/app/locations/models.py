"""Location persistence model.

A location belongs to exactly one restaurant. Sales and forecasts attach to a
location rather than directly to the restaurant. See ``docs/DATA_MODEL.md``
§19–22.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.types import TimestampMixin, UUIDPrimaryKey


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("restaurant_id", "name"),)

    id: Mapped[UUIDPrimaryKey]
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # IANA timezone identifier, e.g. "America/New_York".
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
