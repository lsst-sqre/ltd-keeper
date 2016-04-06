#!/usr/bin/env python

"""Run the ltd-keeper app in development or production mode.

To run in development mode::

    ./run.py --dev

Otherwise::

    ./run.py

will run LTD Keeper with production configurations.

See config/{development.py, production.py} for associated configuration.
"""
import argparse

from app import create_app, db
from app.models import User


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dev', action='store_true', default=False,
                        help='Run in development mode')
    args = parser.parse_args()

    if args.dev:
        environment = 'development'
    else:
        environment = 'production'
    app = create_app(profile=environment)

    with app.app_context():
        db.create_all()
        # bootstrap a user
        if User.query.get(1) is None:
            u = User(username=app.config['DEFAULT_USER'])
            u.set_password(app.config['DEFAULT_PASSWORD'])
            db.session.add(u)
            db.session.commit()
    app.run()
