#!/usr/bin/env python

"""Run the ltd-keeper app in development or production mode.

If this is a new deployment, run

   ./run.py init

To run in development mode::

   ./run.py runserver

In production::

   export LTD_KEEPER_PROFILE=production
   ./run.py run.py runserver

(Though in the Kubernetes deploy this should be run in uwsgi instead)

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


if __name__ == '__main__':
    manager.run()
