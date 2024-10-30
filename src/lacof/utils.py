"""Lacof app utils."""

from collections.abc import AsyncGenerator, Callable

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


# TODO: Remove when https://github.com/psf/black/issues/4254 is fixed
# fmt: off
async def resolve_fastapi_dependency[T](
    dependency: Callable[[], AsyncGenerator[T, None]],
) -> T:
    """Resolve a FastAPI dependency function that returns an async generator.

    Apparently, there's no better way:
    - https://github.com/fastapi/fastapi/discussions/7720
    - https://stackoverflow.com/a/75152604/3023841

    Arguments:
        dependency: FastAPI dependency function.

    Returns:
        Value that the generator yields.
    """
    async_gen = dependency()
    result = await anext(async_gen)

    return result
# fmt: on
