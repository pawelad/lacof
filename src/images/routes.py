"""Images app routes."""

from io import BytesIO
from typing import TYPE_CHECKING, Annotated

import redis.asyncio as redis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from sentence_transformers.util import semantic_search
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from images.models import ImageModel
from images.schemas import Image
from images.services import (
    calculate_and_set_cache_image_model_embeddings,
    get_image_model_embeddings,
    stream_image_data_from_s3,
)
from lacof.db import get_db_session
from lacof.dependencies import get_redis_client, get_s3_client
from lacof.settings import lacof_settings
from lacof.utils import API_ERROR_SCHEMA
from users.auth import get_current_user
from users.schemas import User

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client

images_router = APIRouter(prefix="/images", tags=["images"])

# TODO: Move logic to a separate (service?) file?


# TODO: Pagination?
@images_router.get(
    "/",
    responses={200: {"description": "All available images"}},
)
async def list_images(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> list[Image]:
    """List all images."""
    stmt = select(ImageModel)
    images_orm = await session.scalars(stmt)
    images = [Image.model_validate(image_orm) for image_orm in images_orm]
    return images


@images_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={201: {"description": "Image successfully created"}},
)
async def create_image(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    s3_client: Annotated["S3Client", Depends(get_s3_client)],
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
) -> Image:
    """Upload a new image.

    Only JPG/JPEG and PNG files are allowed.
    """
    # TODO: Try to check if the passed file is actually an image?
    try:
        image_orm = ImageModel(
            user_id=user.id,
            file_name=file.filename,
            file_path=ImageModel.generate_file_path(file.filename),
            content_type=file.content_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    session.add(image_orm)
    await session.commit()
    await session.refresh(image_orm)

    # If it was only S3, we could 'stream' it, but because we also need it for the
    # background task, we might as well load it into memory straight away.
    image_data = BytesIO(await file.read())

    # Upload file to S3
    await s3_client.upload_fileobj(
        Fileobj=image_data,
        Bucket=lacof_settings.S3_BUCKET_NAME,
        Key=image_orm.file_path,
        ExtraArgs={"ContentType": image_orm.content_type},
    )
    # TODO: Check for upload success?

    # Generate and cache Clip model embeddings
    background_tasks.add_task(
        calculate_and_set_cache_image_model_embeddings,
        model=request.state.clip_model,
        image_data=image_data,
        redis_client=redis_client,
        key_name=image_orm.clip_embeddings_cache_key,
    )

    image = Image.model_validate(image_orm)
    return image


@images_router.get(
    "/{image_id}",
    responses={
        200: {"description": "Image requested by ID"},
        404: {"description": "Image not found", "content": API_ERROR_SCHEMA},
    },
)
async def get_image(
    image_id: Annotated[int, Path(title="Image ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> Image:
    """Get image details."""
    stmt = select(ImageModel).where(ImageModel.id == image_id)
    image_orm = await session.scalar(stmt)

    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    image = Image.model_validate(image_orm)
    return image


@images_router.get(
    "/{image_id}/download",
    # Automatically generated OpenAPI schema (and thus docs) for `StreamingResponse`
    # are incorrect (see: https://github.com/fastapi/fastapi/discussions/3881).
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Requested image content",
            "headers": {
                "Transfer-Encoding": {
                    "schema": {"type": "string"},
                    "description": "chunked",
                },
            },
            "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
        },
        404: {"description": "Image not found", "content": API_ERROR_SCHEMA},
    },
)
async def download_image(
    request: Request,
    image_id: Annotated[int, Path(title="Image ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
    s3_client: Annotated["S3Client", Depends(get_s3_client)],
) -> StreamingResponse:
    """Download an image."""
    stmt = select(ImageModel).where(ImageModel.id == image_id)
    image_orm = await session.scalar(stmt)

    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Stream file from S3
    s3_data_stream = await stream_image_data_from_s3(
        s3_client=s3_client,
        bucket_name=lacof_settings.S3_BUCKET_NAME,
        key_name=image_orm.file_path,
    )

    headers = {
        "Content-Disposition": f'inline; filename="{image_orm.file_name}"',
    }

    return StreamingResponse(
        content=s3_data_stream,
        headers=headers,
        media_type=image_orm.content_type,
    )


@images_router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        204: {"description": "Image successfully deleted"},
        404: {"description": "Image not found", "content": API_ERROR_SCHEMA},
    },
)
async def delete_image(
    image_id: Annotated[int, Path(title="Image ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete image."""
    stmt = select(ImageModel).where(ImageModel.id == image_id)
    image_orm = await session.scalar(stmt)

    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    await session.delete(image_orm)
    await session.commit()
