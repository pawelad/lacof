"""Image schemas."""

from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


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


class SimilarImage(BaseModel):
    """Similar image schema.

    Attributes:
        image_id: Image ID.
        similarity: ID of the user that uploaded the image.
    """

    model_config = ConfigDict(from_attributes=True)

    image_id: int
    similarity: Annotated[float, AfterValidator(lambda v: round(v, 5))]


class ImageWithSimilarImages(BaseModel):
    """Image with listed similar images schema.

    Attributes:
        image: Image.
        similar_images: List of similar images.
    """

    model_config = ConfigDict(from_attributes=True)

    image: Image
    similar_images: list[SimilarImage]
