"""Images app routes."""

import io
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from images.models import IMAGE_CONTENT_TYPES, ImageModel
from images.schemas import Image
from lacof.db import get_db_session
from lacof.dependencies import get_s3_bucket
from lacof.utils import API_ERROR_SCHEMA
from users.auth import get_current_user
from users.schemas import User

if TYPE_CHECKING:
    from mypy_boto3_s3.service_resource import Bucket

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
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    s3_bucket: Annotated["Bucket", Depends(get_s3_bucket)],
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

    # Save file to S3
    s3_bucket.upload_fileobj(
        Fileobj=file.file,
        Key=image_orm.file_path,
        ExtraArgs={"ContentType": image_orm.content_type},
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


# TODO: Streaming response?
# TODO: OpenAPI schema (and docs) for `FileResponse` are incorrectly generated
#   (see: https://github.com/fastapi/fastapi/discussions/9551. And even when using
#   base `Response`, it always marks "application/json" as valid content response...
#   (see: https://github.com/fastapi/fastapi/discussions/6650).
@images_router.get(
    "/{image_id}/download",
    response_model=None,
    responses={
        200: {
            "description": "Requested image content",
            "content": {content_type: {} for content_type in IMAGE_CONTENT_TYPES},
        },
        404: {"description": "Image not found", "content": API_ERROR_SCHEMA},
    },
)
async def download_image(
    image_id: Annotated[int, Path(title="Image ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    # TODO: Should auth be separate from `get_current_user`?
    user: Annotated[User, Depends(get_current_user)],
    s3_bucket: Annotated["Bucket", Depends(get_s3_bucket)],
) -> Response:
    """Download an image."""
    stmt = select(ImageModel).where(ImageModel.id == image_id)
    image_orm = await session.scalar(stmt)

    if not image_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    buffer = io.BytesIO()
    s3_bucket.download_fileobj(
        Key=image_orm.file_path,
        Fileobj=buffer,
    )
    buffer.seek(0)

    headers = {"Content-Disposition": f'inline; filename="{image_orm.file_name}"'}

    return Response(
        content=buffer.getvalue(),
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
