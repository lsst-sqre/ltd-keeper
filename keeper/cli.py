"""Command line subcommands for the Flask CLI.

Flask CLI subcommands are implemented with Click. The application factory
(`keeper.appfactory`) registers these
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import alembic
import click
from flask import current_app
from flask.cli import with_appcontext

from keeper.models import Permission, User, db
from keeper.version import get_version

# from psycopg2.errors import UndefinedTable


if TYPE_CHECKING:
    from flask import Flask

__all__ = [
    "add_app_commands",
    "createdb_command",
    "init_command",
    "version_command",
]


def add_app_commands(app: Flask) -> None:
    """Add custom flask subcommands to the Flask app.

    This function is called by `keeper.appfactory.create_flask_app`.
    """
    app.cli.add_command(createdb_command)
    app.cli.add_command(init_command)
    app.cli.add_command(version_command)


@click.command("createdb")
@click.argument("alembicconf")
@with_appcontext
def createdb_command(alembicconf: str) -> None:
    """Deploy the current schema in a new database.

    This database is 'stamped' as having the current alembic schema version.

    Normally, in a new installation, run::

        flask createdb migrations/alembic.ini
        flask init

    This creates the tables and an initial user.

    To migrate database servers, see the copydb sub-command.
    """
    try:
        User.query.get(1)
    except Exception:
        db.create_all()

        # stamp tables with latest schema version
        alembic_cfg = alembic.config.Config(alembicconf)
        alembic.command.stamp(alembic_cfg, "head")


@click.command("init")
@with_appcontext
def init_command() -> None:
    """Initialize the application DB.

    Bootstraps an administrative user given the environment variables:

    - ``LTD_KEEPER_BOOTSTRAP_USER``
    - ``LTD_KEEPER_BOOTSTRAP_PASSWORD``
    """
    if User.query.get(1) is None:
        u = User(
            username=current_app.config["DEFAULT_USER"],
            permissions=Permission.full_permissions(),
        )
        u.set_password(current_app.config["DEFAULT_PASSWORD"])
        db.session.add(u)
        db.session.commit()


@click.command("version")
@with_appcontext
def version_command() -> None:
    """Print the LTD Keeper application version.

    Alternatively, to get the Flask and Python versions, run::

        flask --version
    """
    click.echo(get_version())
