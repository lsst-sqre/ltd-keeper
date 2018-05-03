"""Command line subcommands for the Flask CLI.

Flask CLI subcommands are implemented with Click. The application factory
(`keeper.appfactory`) registers these
"""

__all__ = ('add_app_commands', 'createdb_command', 'init_command',
           'version_command')

import os

import alembic
import click
from flask import current_app
from flask.cli import with_appcontext

from .models import db, User, Permission
from .version import get_version


def add_app_commands(app):
    """Add custom flask subcommands to the Flask app.

    This function is called by `keeper.appfactory.create_flask_app`.
    """
    app.cli.add_command(createdb_command)
    app.cli.add_command(init_command)
    app.cli.add_command(version_command)


@click.command('createdb')
@with_appcontext
def createdb_command():
    """Deploy the current schema in a new database.

    This database is 'stamped' as having the current alembic schema version.

    Normally, in a new installation, run::

        flask createdb
        flask init

    This creates the tables and an initial user.

    To migrate database servers, see the copydb sub-command.
    """
    db.create_all()

    # stamp tables with latest schema version
    config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__),
                     '..',
                     'migrations/alembic.ini'))
    alembic_cfg = alembic.config.Config(config_path)
    alembic.command.stamp(alembic_cfg, "head")


@click.command('init')
@with_appcontext
def init_command():
    """Initialize the application DB.

    Bootstraps an administrative user given the environment variables:

    - ``LTD_KEEPER_BOOTSTRAP_USER``
    - ``LTD_KEEPER_BOOTSTRAP_PASSWORD``
    """
    if User.query.get(1) is None:
        u = User(username=current_app.config['DEFAULT_USER'],
                 permissions=Permission.full_permissions())
        u.set_password(current_app.config['DEFAULT_PASSWORD'])
        db.session.add(u)
        db.session.commit()


@click.command('version')
@with_appcontext
def version_command():
    """Print the LTD Keeper application version.

    Alternatively, to get the Flask and Python versions, run::

        flask --version
    """
    click.echo(get_version())
