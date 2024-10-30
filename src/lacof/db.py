"""Lacof database setup."""

from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import now


class BaseSQLModel(DeclarativeBase):
    """Base lacof database model."""

    id: Mapped[int] = mapped_column(
        primary_key=True,
        sort_order=-10,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=now(),
        sort_order=10,
    )
    modified_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=now(),
        # Per docs, `server_onupdate` does not actually implement any kind of generation
        # function within the database, which instead must be specified separately.
        server_onupdate=now(),
        onupdate=now(),
        sort_order=15,
    )
