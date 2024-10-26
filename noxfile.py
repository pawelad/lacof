"""Lacof Nox sessions."""

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True

DEFAULT_PATHS = ["src/", "tests/", "noxfile.py"]


@nox.session()
def code_style_checks(session: nox.Session) -> None:
    """Check code style."""
    dirs = session.posargs or DEFAULT_PATHS

    # fmt: off
    session.install(
        "black", "isort", "ruff", "interrogate",
        "-c", "requirements/constraints.txt",
    )
    # fmt: on

    session.run("black", "--check", "--diff", *dirs)
    session.run("isort", "--check", "--diff", *dirs)
    session.run("ruff", "check", "--diff", *dirs)
    session.run("interrogate", *dirs)


@nox.session()
def type_checks(session: nox.Session) -> None:
    """Run type checks."""
    dirs = session.posargs or DEFAULT_PATHS

    # fmt: off
    session.install(
        "--no-deps",
        "-r", "requirements/main.txt",
        "-r", "requirements/dev.txt",
    )
    # fmt: on

    session.run("mypy", *dirs)
