"""User auth related code."""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lacof.db import get_db_session
from lacof.models import UserModel
from users.schemas import User

api_key_header = APIKeyHeader(name="X-API-Key")


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    api_key: Annotated[str, Security(api_key_header)],
) -> User:
    """Get current request user.

    Meant to be used as a FastAPI dependency.
    """
    stmt = select(UserModel).where(UserModel.api_key == api_key)
    user_orm = await session.scalar(stmt)

    if not user_orm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )

    user = User.model_validate(user_orm)

    return user