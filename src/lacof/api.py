"""Main lacof API routes config."""

from fastapi import APIRouter

from images.routes import images_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(images_router)
