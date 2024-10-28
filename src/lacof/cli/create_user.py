"""Helper command to create a new user.

Usage:
$ PYTHONPATH=src python -m lacof.cli.create_user {user_name}
"""

import asyncio
import logging
import sys

from sqlalchemy import exc

from lacof.db import get_db_session
from lacof.models import UserModel

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def create_user(username: str) -> None:
    """Create new user.

    User API key is generated automatically on save.

    Arguments:
        username: New user's username.
    """
    # TODO: There has to be a better way...
    #  https://stackoverflow.com/a/75152604/3023841
    #  https://github.com/fastapi/fastapi/discussions/7720
    session_generator = get_db_session()
    session = await anext(session_generator)

    user = UserModel(name=username)
    session.add(user)
    try:
        await session.commit()
    except exc.IntegrityError as e:
        logger.warning(f"Error when trying to create the user: {e!r}")
    else:
        await session.refresh(user)
        logger.info(
            f"Successfully created user '{user.name}' with API key '{user.api_key}'"
        )


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        raise ValueError("Command expects exactly one argument, the username.")

    asyncio.run(create_user(username=args[0]))
