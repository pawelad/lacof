"""Image related service code."""

from collections.abc import AsyncGenerator
from io import BytesIO
from typing import TYPE_CHECKING

import msgpack
import msgpack_numpy
import numpy
import redis.asyncio as redis
from PIL import Image
from sentence_transformers import SentenceTransformer

from images.models import ImageModel

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


async def get_image_data_from_s3(
    *,
    s3_client: "S3Client",
    bucket_name: str,
    key_name: str,
) -> bytes:
    """TODO: Docstrings."""
    # TODO: Error handling (`s3_client.exceptions.NoSuchKey`)?
    s3_image = await s3_client.get_object(
        Bucket=bucket_name,
        Key=key_name,
    )

    body = await s3_image["Body"].read()
    return body


async def stream_image_data_from_s3(
    *,
    s3_client: "S3Client",
    bucket_name: str,
    key_name: str,
) -> AsyncGenerator:
    """TODO: Docstrings."""
    # TODO: Error handling (`s3_client.exceptions.NoSuchKey`)?
    s3_image = await s3_client.get_object(
        Bucket=bucket_name,
        Key=key_name,
    )

    s3_stream = (chunk async for chunk in s3_image["Body"])

    return s3_stream


async def calculate_image_model_embeddings(
    *,
    model: SentenceTransformer,
    image_data: BytesIO,
) -> numpy.ndarray:
    """TODO: Docstrings."""
    image_pil = Image.open(image_data)
    image_embeddings = model.encode(image_pil)  # type: ignore
    image_pil.close()

    return image_embeddings


async def set_cache_image_model_embeddings(
    *,
    redis_client: redis.Redis,
    key_name: str,
    image_embeddings: numpy.ndarray,
) -> bool:
    """TODO: Docstrings."""
    image_embeddings_msgpack = msgpack.packb(
        image_embeddings,
        default=msgpack_numpy.encode,
    )

    response = await redis_client.set(key_name, image_embeddings_msgpack)

    return response


async def get_cache_image_model_embeddings(
    *,
    redis_client: redis.Redis,
    key_name: str,
) -> numpy.ndarray | None:
    """TODO: Docstrings."""
    image_embeddings_msgpack = await redis_client.get(key_name)

    if image_embeddings_msgpack:
        image_embeddings = msgpack.unpackb(
            image_embeddings_msgpack,
            object_hook=msgpack_numpy.decode,
        )
    else:
        image_embeddings = None

    return image_embeddings


# TODO: Too verbose?
async def calculate_and_set_cache_image_model_embeddings(
    *,
    model: SentenceTransformer,
    image_data: BytesIO,
    redis_client: redis.Redis,
    key_name: str,
) -> numpy.ndarray:
    """TODO: Docstrings."""
    image_embeddings = await calculate_image_model_embeddings(
        model=model,
        image_data=image_data,
    )

    await set_cache_image_model_embeddings(
        redis_client=redis_client,
        key_name=key_name,
        image_embeddings=image_embeddings,
    )

    return image_embeddings


async def get_image_model_embeddings(
    *,
    model: SentenceTransformer,
    image: ImageModel,
    redis_client: redis.Redis,
    # TODO: Should this be optional?
    s3_client: "S3Client",
    bucket_name: str,
) -> numpy.ndarray:
    """TODO: Docstrings."""
    redis_key_name = image.clip_embeddings_cache_key
    image_embeddings = await get_cache_image_model_embeddings(
        redis_client=redis_client,
        key_name=redis_key_name,
    )

    # No cache hit - calculate, cache and return the embeddings
    if image_embeddings is None:
        image_data = await get_image_data_from_s3(
            s3_client=s3_client,
            bucket_name=bucket_name,
            key_name=image.file_path,
        )

        image_embeddings = await calculate_and_set_cache_image_model_embeddings(
            model=model,
            image_data=BytesIO(image_data),
            redis_client=redis_client,
            key_name=redis_key_name,
        )

    return image_embeddings
