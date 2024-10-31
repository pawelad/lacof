"""Image related service code."""

import asyncio
import functools
from collections.abc import AsyncGenerator
from io import BytesIO
from typing import TYPE_CHECKING

import msgpack
import msgpack_numpy
import numpy
import redis.asyncio as redis
from PIL import Image
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import _convert_to_tensor, semantic_search
from sqlalchemy import ScalarResult, select
from sqlalchemy.ext.asyncio import AsyncSession

from lacof.images.models import ImageModel
from lacof.images.schemas import SimilarImage
from lacof.settings import lacof_settings

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


async def get_images_from_db(*, db_session: AsyncSession) -> ScalarResult[ImageModel]:
    """Get all available images from the database.

    Arguments:
        db_session: SQLAlchemy async database session.

    Returns:
        All available images.
    """
    stmt = select(ImageModel)
    images_orm = await db_session.scalars(stmt)

    return images_orm


async def get_image_from_db(
    *,
    db_session: AsyncSession,
    image_id: int,
) -> ImageModel | None:
    """Get image with passed ID from the database.

    Arguments:
        db_session: SQLAlchemy async database session.
        image_id: Image ID.

    Returns:
        Requested image, if it exists, `None` otherwise.
    """
    stmt = select(ImageModel).where(ImageModel.id == image_id)
    image_orm = await db_session.scalar(stmt)

    return image_orm


async def save_image_to_db(*, db_session: AsyncSession, image: ImageModel) -> None:
    """Save passed image to the database.

    Arguments:
        db_session: Async SQLAlchemy database session.
        image: Image to save.
    """
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)


async def delete_image_from_db(*, db_session: AsyncSession, image: ImageModel) -> None:
    """Delete passed image from the database.

    Arguments:
        db_session: Async SQLAlchemy database session.
        image: Image to delete.
    """
    await db_session.delete(image)
    await db_session.commit()


async def get_image_data_from_s3(
    *,
    s3_client: "S3Client",
    image: ImageModel,
    bucket_name: str | None = None,
) -> bytes:
    """Get image data from S3.

    Arguments:
        s3_client: Async S3 client.
        image: Image to get the data for.
        bucket_name: S3 bucket name.

    Returns:
        Image file data.
    """
    bucket_name = bucket_name or lacof_settings.S3_BUCKET_NAME

    s3_image = await s3_client.get_object(
        Bucket=bucket_name,
        Key=image.s3_image_data_key,
    )

    body = await s3_image["Body"].read()
    return body


async def stream_image_data_from_s3(
    *,
    s3_client: "S3Client",
    image: ImageModel,
    bucket_name: str | None = None,
) -> AsyncGenerator:
    """Stream image data from S3.

    Arguments:
        s3_client: Async S3 client.
        image: Image to get the data for.
        bucket_name: S3 bucket name.

    Returns:
        Async image file data generator.
    """
    bucket_name = bucket_name or lacof_settings.S3_BUCKET_NAME

    s3_image = await s3_client.get_object(
        Bucket=bucket_name,
        Key=image.s3_image_data_key,
    )

    s3_stream = (chunk async for chunk in s3_image["Body"])

    return s3_stream


async def save_image_data_to_s3(
    *,
    s3_client: "S3Client",
    image: ImageModel,
    image_data: BytesIO,
    bucket_name: str | None = None,
) -> None:
    """Save image data to S3.

    Arguments:
        s3_client: Async S3 client.
        image: Image to save.
        image_data: Image file data.
        bucket_name: S3 bucket name.
    """
    bucket_name = bucket_name or lacof_settings.S3_BUCKET_NAME

    await s3_client.upload_fileobj(
        Fileobj=image_data,
        Bucket=bucket_name,
        Key=image.s3_image_data_key,
        ExtraArgs={"ContentType": image.content_type},
    )


def calculate_image_model_embeddings(
    *,
    model: SentenceTransformer,
    image_data: BytesIO,
) -> numpy.ndarray:
    """Calculate embeddings for passed ML model and image data.

    Arguments:
        model: Pretrained machine learning model.
        image_data: Image file data.

    Returns:
        Image ML model embeddings.
    """
    image_pil = Image.open(image_data)
    image_embeddings = model.encode(image_pil)  # type: ignore
    image_pil.close()

    return image_embeddings


async def set_cache_model_embeddings(
    *,
    redis_client: redis.Redis,
    key_name: str,
    image_embeddings: numpy.ndarray,
) -> bool:
    """Cache passed image ML model embeddings in Redis.

    Arguments:
        redis_client: Async Redis client.
        key_name: Redis key name.
        image_embeddings: Image ML model embeddings.

    Returns:
        Whether the value was successfully saved in Redis.
    """
    image_embeddings_msgpack = msgpack.packb(
        image_embeddings,
        default=msgpack_numpy.encode,
    )

    response = await redis_client.set(key_name, image_embeddings_msgpack)

    return response


async def get_cache_model_embeddings(
    *,
    redis_client: redis.Redis,
    key_name: str,
) -> numpy.ndarray | None:
    """Cache passed image ML model embeddings in Redis.

    Arguments:
        redis_client: Async Redis client.
        key_name: Redis key name.

    Returns:
        Cached image ML model embeddings if they exist, `None` otherwise.
    """
    image_embeddings_msgpack = await redis_client.get(key_name)

    if image_embeddings_msgpack:
        image_embeddings = msgpack.unpackb(
            image_embeddings_msgpack,
            object_hook=msgpack_numpy.decode,
        )
    else:
        image_embeddings = None

    return image_embeddings


async def calculate_and_cache_image_clip_model_embeddings(
    *,
    redis_client: redis.Redis,
    clip_model: SentenceTransformer,
    image_data: BytesIO,
    cache_key: str,
) -> numpy.ndarray:
    """Calculate passed image `Clip` model embeddings and cache them in Redis.

    Arguments:
        redis_client: Async Redis client.
        clip_model: Pretrained `Clip` ML model.
        image_data: Image file data.
        cache_key: Image model embeddings cache key.

    Returns:
        Image ML model embeddings.
    """
    loop = asyncio.get_running_loop()

    # TODO: Should we use `ProcessPoolExecutor`?
    image_embeddings = await loop.run_in_executor(
        executor=None,
        func=functools.partial(
            calculate_image_model_embeddings,
            model=clip_model,
            image_data=image_data,
        ),
    )

    await set_cache_model_embeddings(
        redis_client=redis_client,
        key_name=cache_key,
        image_embeddings=image_embeddings,
    )

    return image_embeddings


async def get_image_model_embeddings(
    *,
    s3_client: "S3Client",
    redis_client: redis.Redis,
    clip_model: SentenceTransformer,
    image: ImageModel,
    bucket_name: str | None = None,
) -> numpy.ndarray:
    """Get (preferably cached) `Clip` ML model embeddings for passed image.

    If the embeddings are cached, get them from Redis. Otherwise, calculate them
    and cache the results.

    Arguments:
        s3_client: Async S3 client.
        redis_client: Async Redis client.
        clip_model: Pretrained `Clip` ML model.
        image: Image to cache the data for.
        bucket_name: S3 bucket name.

    Returns:
        Image ML model embeddings.
    """
    image_embeddings = await get_cache_model_embeddings(
        redis_client=redis_client,
        key_name=image.cache_clip_embeddings_key,
    )

    # No cache hit - calculate and cache ML embeddings
    if image_embeddings is None:
        bucket_name = bucket_name or lacof_settings.S3_BUCKET_NAME

        image_data = await get_image_data_from_s3(
            s3_client=s3_client,
            image=image,
            bucket_name=bucket_name,
        )

        image_embeddings = await calculate_and_cache_image_clip_model_embeddings(
            redis_client=redis_client,
            clip_model=clip_model,
            image_data=BytesIO(image_data),
            cache_key=image.cache_clip_embeddings_key,
        )

    return image_embeddings


async def find_similar_images(
    *,
    db_session: AsyncSession,
    s3_client: "S3Client",
    redis_client: redis.Redis,
    clip_model: SentenceTransformer,
    image: ImageModel,
    bucket_name: str | None = None,
    limit: int = 10,
    threshold: float | None = None,
) -> list[SimilarImage]:
    """Find images similar to passed image using passed `Clip` ML model.

    Arguments:
        db_session: SQLAlchemy async database session.
        s3_client: Async S3 client.
        redis_client: Async Redis client.
        clip_model: Pretrained `Clip` ML model.
        image: Image to cache the data for.
        bucket_name: S3 bucket name.
        limit: Limit of similar images to return.
        threshold: Similarity threshold.

    Returns:
        List of similar images and their similarity score.
    """
    bucket_name = bucket_name or lacof_settings.S3_BUCKET_NAME

    # Main image embeddings
    query_embeddings = await get_image_model_embeddings(
        s3_client=s3_client,
        redis_client=redis_client,
        clip_model=clip_model,
        image=image,
        bucket_name=bucket_name,
    )

    # Get all other images
    stmt = select(ImageModel).where(ImageModel.id != image.id)
    other_images_orm = await db_session.scalars(stmt)

    # Get embeddings for those images
    corpus_embeddings_image_ids = []
    corpus_embeddings = []
    for image_orm in other_images_orm:
        image_embeddings = await get_image_model_embeddings(
            s3_client=s3_client,
            redis_client=redis_client,
            clip_model=clip_model,
            image=image_orm,
            bucket_name=bucket_name,
        )

        corpus_embeddings_image_ids.append(image_orm.id)

        corpus_embeddings.append(_convert_to_tensor(image_embeddings))

    # Find best matches
    # TODO: Try to fix `UserWarning: The given NumPy array is not writable,
    #  and PyTorch does not support non-writable tensors.`
    # TODO: Maybe cache this and invalidate when a new image is uploaded?
    matches = semantic_search(
        query_embeddings=query_embeddings,  # type: ignore
        corpus_embeddings=corpus_embeddings,  # type: ignore
        top_k=limit,
    )[0]

    similar_images = []
    for match in matches:
        corpus_id, similarity = match["corpus_id"], match["score"]
        assert isinstance(corpus_id, int)  # For mypy

        if threshold and similarity < threshold:
            continue

        image_id = corpus_embeddings_image_ids[corpus_id]
        similar_image = SimilarImage(image_id=image_id, similarity=similarity)
        similar_images.append(similar_image)

    return similar_images
