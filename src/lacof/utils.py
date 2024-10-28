"""Lacof app utils."""

from fastapi.openapi.constants import REF_PREFIX

# Source: https://github.com/fastapi/fastapi/blob/adf89d1d9fdc8ea03bc0f3361b3d5e4b6835cf6c/fastapi/openapi/utils.py#L404-L411
API_ERROR_SCHEMA = {
    "application/json": {
        "schema": {
            "$ref": REF_PREFIX + "HTTPValidationError",
        }
    }
}
