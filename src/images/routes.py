"""Images app routes."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from images.models import ImageModel
from images.schemas import Image
from lacof.db import get_db_session
from lacof.dependencies import get_s3_bucket
from users.auth import get_current_user
from users.schemas import User

if TYPE_CHECKING:
    from mypy_boto3_s3.service_resource import Bucket

images_router = APIRouter(prefix="/images", tags=["images"])

# TODO: Move logic to a separate (service?) file?


@images_router.get("/")
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


@images_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_image(
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    s3_bucket: Annotated["Bucket", Depends(get_s3_bucket)],
) -> Image:
    """Upload a new image."""
    image_orm = ImageModel(
        user_id=user.id,
        file_name=file.filename,
        file_path=ImageModel.generate_file_path(file.filename),
        content_type=file.content_type,
    )
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


@images_router.get("/{image_id}")
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


@images_router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
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
