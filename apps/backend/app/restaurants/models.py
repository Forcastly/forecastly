"""Restaurant and membership persistence models.

The restaurant is Forecastly's tenant boundary. Users gain access through
``restaurant_memberships`` rather than direct ownership. See
``docs/DATA_MODEL.md`` §13–18.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base
from app.core.db.types import TimestampMixin, UUIDPrimaryKey

ROLE_OWNER = "owner"
ROLE_MEMBER = "member"


class Restaurant(TimestampMixin, Base):
    __tablename__ = "restaurants"

    id: Mapped[UUIDPrimaryKey]
    name: Mapped[str] = mapped_column(Text, nullable=False)

    memberships: Mapped[list[RestaurantMembership]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )


class RestaurantMembership(TimestampMixin, Base):
    __tablename__ = "restaurant_memberships"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "user_id"),
        CheckConstraint("role IN ('owner', 'member')", name="role_valid"),
    )

    id: Mapped[UUIDPrimaryKey]
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="memberships")
