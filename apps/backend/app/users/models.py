"""User and external-identity persistence models.

Forecastly owns its ``users.id`` (UUID). External auth-provider identifiers live
in ``user_identities`` — never as a domain primary key. See
``docs/DATA_MODEL.md`` §8–12.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base
from app.core.db.types import TimestampMixin, UUIDPrimaryKey


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUIDPrimaryKey]
    email: Mapped[str] = mapped_column(Text, nullable=False)

    identities: Mapped[list[UserIdentity]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserIdentity(TimestampMixin, Base):
    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_subject"),)

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_subject: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="identities")
