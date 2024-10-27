"""Lacof app shared dependencies."""

from typing import TYPE_CHECKING, Annotated

import boto3
from fastapi import Depends

from lacof.settings import lacof_settings

if TYPE_CHECKING:
    from mypy_boto3_s3.service_resource import Bucket, S3ServiceResource


async def get_s3_resource() -> "S3ServiceResource":
    """Initialize and return a `boto3` S3 resource."""
    s3 = boto3.resource(
        "s3",
        endpoint_url=str(lacof_settings.S3_ENDPOINT_URL),
        aws_access_key_id=lacof_settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=lacof_settings.AWS_SECRET_ACCESS_KEY.get_secret_value(),
    )
    return s3


async def get_s3_bucket(
    s3_resource: Annotated["S3ServiceResource", Depends(get_s3_resource)],
) -> "Bucket":
    """Initialize and return `boto3` S3 bucket."""
    bucket = s3_resource.Bucket(lacof_settings.S3_BUCKET_NAME)
    return bucket
