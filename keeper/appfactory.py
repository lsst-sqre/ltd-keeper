"""Flask application factory.

Applies configurations, creates the DB schema (if necessary) and registers
all HTTP routes.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

__all__ = ('create_flask_app',)

import os

from flask import Flask

from .config import config


def create_flask_app(profile=None):
    """Create an application instance.

    This is called by a runner script, such as /run.py.
    """
    app = Flask('keeper')

    # Apply configuration
    if profile is None:
        # Let Python API clients (like pytest) set the profile directly
        # Otherwise, the profile is obtained from the shell environment.
        profile = os.getenv('LTD_KEEPER_PROFILE', 'development')
    app.config.from_object(config[profile])
    config[profile].init_app(app)

    # Initialize the database interface
    from .models import db
    db.init_app(app)

    # Register blueprints
    from .api_v1 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix=None)

    return app
