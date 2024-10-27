"""Lacof main ASGI app."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from lacof import __title__, __version__
from lacof.api import api_router
from lacof.settings import lacof_settings

application = FastAPI(
    debug=lacof_settings.DEBUG,
    title=__title__,
    version=__version__,
    docs_url=None,
    redoc_url="/api/v1/docs",
)

# Main API router
application.include_router(api_router)


@application.get("/", include_in_schema=False)
async def root() -> Response:
    """Redirect user to API docs."""
    return RedirectResponse("/api/v1/docs")


# Static files
application.mount("/static", StaticFiles(directory="static"), name="static")
