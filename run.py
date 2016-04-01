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

from app import create_app, db
from app.models import User, Permission

environment = os.getenv('LTD_KEEPER_PROFILE', 'development')
keeper_app = create_app(profile=environment)
manager = Manager(keeper_app)


@manager.command
def init():
    """Initialize the application DB."""
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
