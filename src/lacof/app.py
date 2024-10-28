"""Lacof main ASGI app."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TypedDict

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer

from lacof import __title__, __version__
from lacof.api import api_router
from lacof.settings import lacof_settings


class State(TypedDict):
    """Lacof FastAPI state schema."""

    redis_connection_pool: redis.ConnectionPool
    context_stack: AsyncExitStack
    clip_model: SentenceTransformer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    """Manage app startup and shutdown."""
    # Redis connection pool
    redis_pool = redis.ConnectionPool.from_url(str(lacof_settings.REDIS_URL))

    # This is needed for using `aioboto3` without 'Unclosed client session' warnings
    # See:
    #  - https://github.com/terricain/aioboto3/issues/338
    #  - https://aioboto3.readthedocs.io/en/latest/usage.html#aiohttp-server-example
    context_stack = AsyncExitStack()

    # Load CLIP model
    clip_model = SentenceTransformer(lacof_settings.CLIP_MODEL_NAME)

    yield {
        "context_stack": context_stack,
        "clip_model": clip_model,
        "redis_connection_pool": redis_pool,
    }

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
