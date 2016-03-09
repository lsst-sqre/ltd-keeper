#!/usr/bin/env python

"""Run the ltd-keeper app in development or production mode.

To run in development mode, specifically set::

    export LTD_KEEPER_CONFIG=development

The default is equivalent to::

    export LTD_KEEPER_CONFIG=production

See config/{development.py, production.py} for associated configuration.
"""
import os
from app import create_app, db
from app.models import User


if __name__ == '__main__':
    app = create_app(os.environ.get('LTD_KEEPER_CONFIG', 'production'))
    with app.app_context():
        db.create_all()
        # create a development user
        if User.query.get(1) is None:
            u = User(username=app.config['DEFAULT_USER'])
            u.set_password(app.config['DEFAULT_PASSWORD'])
            db.session.add(u)
            db.session.commit()
    app.run()
