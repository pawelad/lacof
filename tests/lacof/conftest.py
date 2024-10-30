"""Shared lacof test fixtures."""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lacof.db import BaseSQLModel
from lacof.settings import lacof_settings
from users.auth import api_key_header
from users.models import UserModel

# TODO: Fixtures scopes?


@pytest_asyncio.fixture(name="db_session")
async def db_session_fixture() -> AsyncGenerator[AsyncSession, None]:
    """Initialize test async SQLAlchemy database session.

    Source:
        https://chaoticengineer.hashnode.dev/fastapi-sqlalchemy
    """
    engine = create_async_engine(
        str(lacof_settings.TEST_DATABASE_URL),
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(BaseSQLModel.metadata.create_all)

    factory = async_sessionmaker(engine)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseSQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(name="test_app")
def test_app_fixture(db_session: AsyncSession) -> Generator[FastAPI]:
    """Create a test app with overridden dependencies."""
    from lacof.app import application
    from lacof.dependencies import get_db_session

    application.dependency_overrides[get_db_session] = lambda: db_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture(name="test_client")
async def test_client_fixture(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create a test async HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(name="test_user")
async def test_user_fixture(db_session: AsyncSession) -> UserModel:
    """Create and return a test user."""
    user = UserModel(name="test_user", api_key="TEST_API_KEY")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture(name="auth_header")
async def auth_header_fixture(test_user: UserModel) -> dict:
    """Return valid API auth header."""
    header_name = api_key_header.model.name
    headers = {header_name: test_user.api_key}
    return headers
