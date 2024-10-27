"""Image schemas."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Image(BaseModel):
    """Image schema.

    Attributes:
        id: Image ID.
        user_id: ID of the user that uploaded the image.
        file_name: Image file name.
        file_path: Image file path.
        content_type: File content type.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    file_name: str
    file_path: Path
    content_type: str
