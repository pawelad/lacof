"""Main lacof API routes config."""

from typing import Annotated

from fastapi import APIRouter, Depends

from lacof import __version__
from lacof.images.routes import images_router
from lacof.settings import lacof_settings
from lacof.users.auth import get_current_user
from lacof.users.schemas import User
from lacof.utils import APIInfo

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(images_router)


@api_router.get("/info")
async def info(user: Annotated[User, Depends(get_current_user)]) -> APIInfo:
    """Show API info."""
    api_info = APIInfo(
        version=__version__,
        environment=lacof_settings.ENVIRONMENT,
        user=user.name,
    )
    return api_info
