"""Lacof main ASGI app."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from lacof import __title__, __version__
from lacof.api import api_router
from lacof.settings import lacof_settings


class State(TypedDict):
    """Lacof FastAPI state schema."""

    context_stack: AsyncExitStack


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    """Manage app startup and shutdown.

    This was needed for `get_s3_client`, as trying to implement it without the
    `AsyncExitStack` resulted in 'Unclosed client session' warnings.
    """
    context_stack = AsyncExitStack()

    yield {"context_stack": context_stack}

    await context_stack.aclose()


application = FastAPI(
    debug=lacof_settings.DEBUG,
    title=__title__,
    version=__version__,
    docs_url=None,
    redoc_url="/api/v1/docs",
    lifespan=lifespan,
)

# Main API router
application.include_router(api_router)


@application.get("/", include_in_schema=False)
async def root() -> Response:
    """Redirect user to API docs."""
    return RedirectResponse("/api/v1/docs")


# Static files
application.mount("/static", StaticFiles(directory="static"), name="static")
