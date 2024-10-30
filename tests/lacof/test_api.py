"""Test `lacof.api` module."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from lacof import __version__


@pytest.mark.asyncio
async def test_api_info(test_client: AsyncClient, auth_header: dict) -> None:
    """Should return API info."""
    response = await test_client.get("/api/v1/info", headers=auth_header)
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data["version"] == __version__
    assert data["environment"] == "test"
    assert data["user"] == "test_user"
