"""Images database models."""

import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lacof.db import BaseSQLModel

if TYPE_CHECKING:
    from users.models import UserModel


class ImageModel(BaseSQLModel):
    """Image database model."""

    __tablename__ = "image"

    user: Mapped["UserModel"] = relationship(back_populates="images")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(128))

    @classmethod
    def generate_file_path(cls, file_name: str | None) -> str:
        """Generate unique file path.

        Arguments:
            file_name: File name to generate the path for. If empty, a random string
                will be used.
        """
        directory = Path(cls.__tablename__)

        if file_name:
            file_name_path = Path(file_name)
            file_name_stem = file_name_path.stem
            file_extension = file_name_path.suffix
            suffix = secrets.token_hex(16)

            new_file_name = f"{file_name_stem}-{suffix}{file_extension}"
        else:
            new_file_name = secrets.token_hex(32)

        file_path = directory / new_file_name

        return str(file_path)
