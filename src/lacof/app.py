"""Lacof main ASGI app."""

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from lacof import __title__, __version__
from lacof.settings import lacof_settings

application = FastAPI(
    debug=lacof_settings.DEBUG,
    title=__title__,
    version=__version__,
    docs_url=None,
    redoc_url="/api/v1/docs",
)

# Static files
application.mount("/static", StaticFiles(directory="static"), name="static")
