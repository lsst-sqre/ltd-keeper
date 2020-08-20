"""Flask application factory.
"""

__all__ = ("create_flask_app",)

import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .cli import add_app_commands
from .config import config


def create_flask_app(profile=None):
    """Create an application instance.

    This is called from ``__init__.py`` to create the `keeper.flask_app`
    instance that is used by uwsgi and the Flask CLI.
    """
    app = Flask("keeper")

    # Apply configuration
    if profile is None:
        # Let Python API clients (like pytest) set the profile directly
        # Otherwise, the profile is obtained from the shell environment.
        profile = os.getenv("LTD_KEEPER_PROFILE", "development")
    app.config.from_object(config[profile])
    config[profile].init_app(app)

    # Add the middleware to respect headers forwarded from the proxy server
    if app.config["PROXY_FIX"]:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config["TRUST_X_FOR"],
            x_proto=app.config["TRUST_X_PROTO"],
            x_host=app.config["TRUST_X_HOST"],
            x_port=app.config["TRUST_X_PORT"],
            x_prefix=app.config["TRUST_X_PREFIX"],
        )

    # Initialize the celery app
    from .celery import create_celery_app

    create_celery_app(app)

    # Initialize the Flask-SQLAlchemy  database interface and
    # initialize Alembic migrations through Flask-Migrate
    from .models import db, migrate

    db.init_app(app)
    migrate.init_app(
        app, db, compare_type=True, render_as_batch=True  # for autogenerate
    )  # for sqlite; safe for other servers

    # Register blueprints
    from .api import api as api_blueprint

    app.register_blueprint(api_blueprint, url_prefix=None)

    # Add custom Flask CLI subcommands
    add_app_commands(app)

    return app
