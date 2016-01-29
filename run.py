#!/usr/bin/env python

"""Run the ltd-keeper app in development mode.

See config/development.py for associated configuration.
"""
import os
from app import create_app, db
from app.models import User

if __name__ == '__main__':
    app = create_app(os.environ.get('LTD_KEEPER_CONFIG', 'development'))
    with app.app_context():
        db.create_all()
        # create a development user
        if User.query.get(1) is None:
            u = User(username='user')
            u.set_password('pass')
            db.session.add(u)
            db.session.commit()
    app.run()
