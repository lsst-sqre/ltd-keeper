#!/usr/bin/env python

"""Run the ltd-keeper app in development or production mode.

If this is a new deployment, run

   ./run.py db upgrade
   ./run.py init

To run in development mode::

   ./run.py runserver

In production::

   export LTD_KEEPER_PROFILE=production
   ./run.py run.py runserver

(Though in the Kubernetes deploy this should be run in uwsgi instead)

will run LTD Keeper with production configurations.

Other commands
--------------

./run.py init
   Initialize a DB. This command is only run once.

./run.py shell
   A Python REPL with `models`, `db` and `keeper_app` available.

./run.py db migrate -m {message}
   Create a migration script with given message.

./run.py db upgrade
   Run a DB migration to the current DB scheme.

./run.py version
   Print the application version.

See keeper/config.py for associated configuration.
"""

import os

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

import keeper
from keeper.models import User, Permission

environment = os.getenv('LTD_KEEPER_PROFILE', 'development')
keeper_app = keeper.create_app(profile=environment)
manager = Manager(keeper_app)

migrate = Migrate(keeper_app, keeper.db,
                  compare_type=True,  # for autogenerate
                  render_as_batch=True)  # for sqlite; safe for other servers
manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    """Pre-populate the shell environment when running run.py shell."""
    return dict(app=keeper_app, db=keeper.db, models=keeper.models)


@manager.command
def createdb():
    """Deploy the current schema in a new database.

    This database is 'stamped' as having the current alembic schema version.

    Normally, in a new installtion, run::

        ./run.py createdb
        ./run.py init

    to both create the tables and an initial user.

    To migrate database servers, see the copydb sub-command.
    """
    keeper.db.create_all()

    # stamp tables with latest schema version
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("migrations/alembic.ini")
    command.stamp(alembic_cfg, "head")


@manager.command
def init():
    """Initialize the application DB.

    ::
        run.py init

    Bootstraps an administrative user given the environment variables:

    - `LTD_KEEPER_BOOTSTRAP_USER`
    - `LTD_KEEPER_BOOTSTRAP_PASSWORD`
    """
    with keeper_app.app_context():
        # bootstrap a user
        if User.query.get(1) is None:
            u = User(username=keeper_app.config['DEFAULT_USER'],
                     permissions=Permission.full_permissions())
            u.set_password(keeper_app.config['DEFAULT_PASSWORD'])
            keeper.db.session.add(u)
            keeper.db.session.commit()


@manager.command
def copydb():
    """Copy data from a source database to the currently-configured DB.

    Use this command to migrate between databases (even across SQL
    implementations, such as from sqlite to MySQL).

    Full run example, including setting up schema in new database::

       export SOURCE_DB_URL=...
       ./run.py createdb
       ./run.py copydb

    The LTD_KEEPER_DB_URL should refer to the new database. The connection
    URI to the *source* database should be specified in the SOURCE_DB_URL
    environment variable.
    """
    from app.dbcopy import Crossover
    source_uri = os.getenv('SOURCE_DB_URL')
    target_uri = os.getenv('LTD_KEEPER_DB_URL')
    assert source_uri is not None
    assert target_uri is not None
    crossover = Crossover(source_uri, target_uri, bulk=10000)
    crossover.copy_data_in_transaction()


@manager.command
def initkeys():
    """Temporary command to add surrogate keys to Products."""
    import uuid
    with keeper_app.app_context():
        for product in keeper.models.Product.query.all():
            if product.surrogate_key is None:
                print('Adding surrogate key to {0}'.format(product.slug))
                product.surrogate_key = uuid.uuid4().hex
                try:
                    keeper.db.session.add(product)
                    keeper.db.session.commit()
                except Exception:
                    keeper.db.session.rollback()
                    print('Failed to make surrogate key for {0}'.format(
                          product.slug))


@manager.command
def version():
    """Print the application version.
    """
    print(keeper.__version__)


if __name__ == '__main__':
    manager.run()
