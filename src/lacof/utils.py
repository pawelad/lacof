"""Lacof app utils."""

from fastapi.openapi.constants import REF_PREFIX
from pydantic import BaseModel

# Source: https://github.com/fastapi/fastapi/blob/adf89d1d9fdc8ea03bc0f3361b3d5e4b6835cf6c/fastapi/openapi/utils.py#L404-L411
API_ERROR_SCHEMA = {
    "application/json": {
        "schema": {
            "$ref": REF_PREFIX + "HTTPValidationError",
        }
    }
}


class APIInfo(BaseModel):
    """API info schema.

    Attributes:
        version: App version. Not to be confused with API version.
        environment: App environment. Can be one either "local" or "production".
        user: Current API user.
    """

    version: str
    environment: str
    user: str
