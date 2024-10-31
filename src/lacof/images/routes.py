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
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lacof.dependencies import get_db_session, get_redis_client, get_s3_client
from lacof.images import services as image_service
from lacof.images.models import ImageModel
from lacof.images.schemas import Image, ImageWithSimilarImages
from lacof.users.auth import get_current_user
from lacof.users.schemas import User
from lacof.utils import API_ERROR_SCHEMA

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client

images_router = APIRouter(prefix="/images", tags=["images"])


@images_router.get(
    "/",
    responses={status.HTTP_200_OK: {"description": "All available images"}},
)
async def list_images(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> list[Image]:
    """List all available images."""
    # TODO: Pagination?
    images_orm = await image_service.get_images_from_db(db_session=db_session)
    images = [Image.model_validate(image_orm) for image_orm in images_orm]

    return images


@images_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_201_CREATED: {"description": "Image successfully created"}},
)
async def create_image(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
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

    await image_service.save_image_to_db(db_session=db_session, image=image_orm)

    # If it was only S3, we could 'stream' it, but because we also need it for the
    # background task, we might as well load it into memory straight away.
    image_data = BytesIO(await file.read())

    # Upload file to S3
    await image_service.save_image_data_to_s3(
        s3_client=s3_client,
        image=image_orm,
        image_data=image_data,
    )

    # Generate and cache Clip model embeddings as a background task
    background_tasks.add_task(
        image_service.calculate_and_cache_image_clip_model_embeddings,
        redis_client=redis_client,
        clip_model=request.state.clip_model,
        image_data=image_data,
        cache_key=image_orm.cache_clip_embeddings_key,
    )

    image = Image.model_validate(image_orm)

    return image


@images_router.get(
    "/{image_id}",
    responses={
        status.HTTP_200_OK: {"description": "Image requested by ID"},
        status.HTTP_404_NOT_FOUND: {
            "description": "Image not found",
            "content": API_ERROR_SCHEMA,
        },
    },
)
async def get_image(
    image_id: Annotated[int, Path(title="Image ID")],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> Image:
    """Get image details."""
    image_orm = await image_service.get_image_from_db(
        db_session=db_session,
        image_id=image_id,
    )
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
        status.HTTP_200_OK: {
            "description": "Requested image content",
            "headers": {
                "Transfer-Encoding": {
                    "schema": {"type": "string"},
                    "description": "chunked",
                },
            },
            "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Image not found",
            "content": API_ERROR_SCHEMA,
        },
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Image missing from S3",
            "content": API_ERROR_SCHEMA,
        },
    },
)
async def download_image(
    request: Request,
    image_id: Annotated[int, Path(title="Image ID")],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
    s3_client: Annotated["S3Client", Depends(get_s3_client)],
) -> StreamingResponse:
    """Download an image."""
    image_orm = await image_service.get_image_from_db(
        db_session=db_session,
        image_id=image_id,
    )
    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Stream file from S3
    try:
        s3_data_stream = await image_service.stream_image_data_from_s3(
            s3_client=s3_client,
            image=image_orm,
        )
    except s3_client.exceptions.NoSuchKey as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Image missing from S3",
        ) from e

    headers = {
        "Content-Disposition": f'inline; filename="{image_orm.file_name}"',
    }

    return StreamingResponse(
        content=s3_data_stream,
        headers=headers,
        media_type=image_orm.content_type,
    )


@images_router.get("/{image_id}/similar")
async def get_similar_images(
    request: Request,
    image_id: Annotated[int, Path(title="Image ID")],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
    s3_client: Annotated["S3Client", Depends(get_s3_client)],
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
    limit: Annotated[int, Query(title="Number of similar images to show")] = 10,
    threshold: Annotated[float, Query(title="Similarity threshold")] = 0.8,
) -> ImageWithSimilarImages:
    """Find similar images among other uploaded ones."""
    main_image_orm = await image_service.get_image_from_db(
        db_session=db_session,
        image_id=image_id,
    )
    if not main_image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    try:
        similar_images = await image_service.find_similar_images(
            db_session=db_session,
            s3_client=s3_client,
            redis_client=redis_client,
            clip_model=request.state.clip_model,
            image=main_image_orm,
            limit=limit,
            threshold=threshold,
        )
    except s3_client.exceptions.NoSuchKey as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Image(s) missing from S3",
        ) from e

    response = ImageWithSimilarImages(
        image=main_image_orm,
        similar_images=similar_images,
    )

    return response


@images_router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Image successfully deleted"},
        status.HTTP_404_NOT_FOUND: {
            "description": "Image not found",
            "content": API_ERROR_SCHEMA,
        },
    },
)
async def delete_image(
    image_id: Annotated[int, Path(title="Image ID")],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete image."""
    image_orm = await image_service.get_image_from_db(
        db_session=db_session,
        image_id=image_id,
    )
    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    await image_service.delete_image_from_db(
        db_session=db_session,
        image=image_orm,
    )
