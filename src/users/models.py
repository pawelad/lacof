"""Users database models."""

import secrets
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lacof.db import BaseSQLModel

if TYPE_CHECKING:
    from images.models import ImageModel


class UserModel(BaseSQLModel):
    """User database model."""

    __tablename__ = "user"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        default=partial(secrets.token_urlsafe, 32),
    )

    images: Mapped[list["ImageModel"]] = relationship(back_populates="user")
