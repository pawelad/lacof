"""Lacof app models.

Models imported here will have migrations automatically handled by `alembic`.
"""

from lacof.db import BaseSQLModel  # noqa
from lacof.images.models import ImageModel  # noqa
from lacof.users.models import UserModel  # noqa
