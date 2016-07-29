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

See config.py for associated configuration.
"""

import os

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from app import create_app, db, models
from app.models import User, Permission

environment = os.getenv('LTD_KEEPER_PROFILE', 'development')
keeper_app = create_app(profile=environment)
manager = Manager(keeper_app)

migrate = Migrate(keeper_app, db)
manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    """Pre-populate the shell environment when running run.py shell."""
    return dict(app=keeper_app, db=db, models=models)


@manager.command
def init():
    """Initialize the application DB.

    ::
        run.py init

    This creates the table schema in a new DB (not overwriting an exisiting
    one) and also bootstraps an administrative user given the environment
    variables

    - `LTD_KEEPER_BOOTSTRAP_USER`
    - `LTD_KEEPER_BOOTSTRAP_PASSWORD`
    """
    with keeper_app.app_context():
        # bootstrap a user
        if User.query.get(1) is None:
            u = User(username=keeper_app.config['DEFAULT_USER'],
                     permissions=Permission.full_permissions())
            u.set_password(keeper_app.config['DEFAULT_PASSWORD'])
            db.session.add(u)
            db.session.commit()


@manager.command
def copydb():
    """Copy data from a source database to the currently-configured DB.

    Use this command to migrate between databases (even across SQL
    implementations, such as from sqlite to MySQL).

    Full run example, including setting up schema in new database::

       export SOURCE_DB_URL=...
       ./run.py db upgrade
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


if __name__ == '__main__':
    manager.run()
