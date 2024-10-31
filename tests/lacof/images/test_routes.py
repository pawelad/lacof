"""Test `lacof.images.routes` module."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from images.models import ImageModel
from images.schemas import Image
from images.services import save_image_to_db
from users.models import UserModel

# TODO: Test model factories?


@pytest.mark.asyncio
async def test_list_images(
    test_client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel,
    auth_header: dict,
) -> None:
    """Return serialised `ImageModel` objects from the database."""
    endpoint_url = "/api/v1/images/"

    # No images in the database
    response = await test_client.get(endpoint_url, headers=auth_header)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []

    # Images present in the database
    image1 = ImageModel(
        user_id=test_user.id,
        file_name="test_filename",
        file_path=ImageModel.generate_file_path("test_filename"),
        content_type="image/jpeg",
    )
    image2 = ImageModel(
        user_id=test_user.id,
        file_name="test_filename",
        file_path=ImageModel.generate_file_path("test_filename"),
        content_type="image/jpeg",
    )
    await save_image_to_db(sql_session=db_session, image=image1)
    await save_image_to_db(sql_session=db_session, image=image2)

    response = await test_client.get(endpoint_url, headers=auth_header)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert data[0] == Image.model_validate(image1).model_dump(mode="json")
    assert data[1] == Image.model_validate(image2).model_dump(mode="json")


# TODO: Test `create_image` API endpoint


@pytest.mark.asyncio
async def test_get_image(
    test_client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel,
    auth_header: dict,
) -> None:
    """Return serialised `ImageModel` object from the database.

    Return HTTP 404 if it doesn't exist.
    """
    endpoint_url = "/api/v1/images/1"

    # No images in the database
    response = await test_client.get(endpoint_url, headers=auth_header)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Image present in the database
    image = ImageModel(
        user_id=test_user.id,
        file_name="test_filename",
        file_path=ImageModel.generate_file_path("test_filename"),
        content_type="image/jpeg",
    )
    await save_image_to_db(sql_session=db_session, image=image)

    response = await test_client.get(endpoint_url, headers=auth_header)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == Image.model_validate(image).model_dump(mode="json")


# TODO: Test `download_image` API endpoint
# TODO: Test `get_similar_images` API endpoint


@pytest.mark.asyncio
async def test_delete_image(
    test_client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel,
    auth_header: dict,
) -> None:
    """Delete `ImageModel` object from the database.

    Return HTTP 404 if it doesn't exist.
    """
    endpoint_url = "/api/v1/images/1"

    # No images in the database
    response = await test_client.delete(endpoint_url, headers=auth_header)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Image present in the database
    image = ImageModel(
        user_id=test_user.id,
        file_name="test_filename",
        file_path=ImageModel.generate_file_path("test_filename"),
        content_type="image/jpeg",
    )
    await save_image_to_db(sql_session=db_session, image=image)

    response = await test_client.delete(endpoint_url, headers=auth_header)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    stmt = select(ImageModel).where(ImageModel.id == 1).exists()
    image_exists = await db_session.scalar(select(stmt))

    assert image_exists is False
