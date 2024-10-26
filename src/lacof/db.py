"""Lacof database setup."""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import now

from lacof.settings import lacof_settings


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


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async SQLAlchemy database session.

    Meant to be used as a FastAPI dependency.

    Source:
        https://chaoticengineer.hashnode.dev/fastapi-sqlalchemy#heading-session-handler
    """
    engine = create_async_engine(str(lacof_settings.DATABASE_URL))
    factory = async_sessionmaker(engine)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except exc.SQLAlchemyError:
            await session.rollback()
            raise
