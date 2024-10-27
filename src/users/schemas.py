"""Users schemas."""

from pydantic import BaseModel, ConfigDict, SecretStr


class User(BaseModel):
    """User schema.

    Attributes:
        id: User ID.
        name: Username.
        api_key: User's API key.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    api_key: SecretStr
