"""Lacof app shared dependencies."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import aioboto3
import redis.asyncio as redis
from fastapi import Request
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lacof.settings import lacof_settings

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


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


async def get_s3_client(request: Request) -> AsyncGenerator["S3Client", None]:
    """Initialize and return a `aioboto3` S3 client.

    Meant to be used as a FastAPI dependency.

    This was surprisingly complicated and resulted in 'Unclosed client session' warnings
    when used without the `AsyncExitStack` (with just `async with session.client()`).
    See:
     - https://github.com/terricain/aioboto3/issues/338
     - https://aioboto3.readthedocs.io/en/latest/usage.html#aiohttp-server-example
    """
    session = aioboto3.Session()

    s3_client = await request.state.context_stack.enter_async_context(
        session.client(
            "s3",
            endpoint_url=str(lacof_settings.S3_ENDPOINT_URL),
            aws_access_key_id=lacof_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=lacof_settings.AWS_SECRET_ACCESS_KEY.get_secret_value(),
        )
    )
    yield s3_client


async def get_redis_client(request: Request) -> AsyncGenerator["redis.Redis", None]:
    """Initialize and return a Redis client.

    Meant to be used as a FastAPI dependency.
    """
    redis_connection_pool = request.state.redis_connection_pool
    redis_client = redis.Redis(connection_pool=redis_connection_pool)
    yield redis_client
    await redis_client.aclose()
