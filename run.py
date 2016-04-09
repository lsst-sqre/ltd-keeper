#!/usr/bin/env python

"""Run the ltd-keeper app in development or production mode.

This will also bootstrap the database if an existing DB is not available.

To run in development mode::

    ./run.py runserver

Otherwise::

    export LTD_KEEPER_PROFILE=production
    python run.py runserver

will run LTD Keeper with production configurations.

See config.py for associated configuration.
"""
import os

from flask.ext.script import Manager

from app import create_app, db, models
from app.models import User, Permission

environment = os.getenv('LTD_KEEPER_PROFILE', 'development')
keeper_app = create_app(profile=environment)
manager = Manager(keeper_app)


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
    _app_db_init()


def _app_db_init():
    """Initialize the DB and add a bootstrap user."""
    with keeper_app.app_context():
        # bootstrap database
        db.create_all()

        # bootstrap a user
        if User.query.get(1) is None:
            u = User(username=keeper_app.config['DEFAULT_USER'],
                     permissions=Permission.full_permissions())
            u.set_password(keeper_app.config['DEFAULT_PASSWORD'])
            db.session.add(u)
            db.session.commit()


# In development mode always try to initialize the DB for easy testing
# Production should use a container that runs the init command.
if environment == 'development':
    _app_db_init()


if __name__ == '__main__':
    manager.run()
