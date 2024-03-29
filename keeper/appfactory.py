"""Flask application factory."""

from __future__ import annotations

import os
from typing import Optional

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from keeper.config import config

__all__ = ["create_flask_app"]


def create_flask_app(profile: Optional[str] = None) -> Flask:
    """Create an application instance.

    This is called from ``__init__.py`` to create the `keeper.flask_app`
    instance that is used by uwsgi and the Flask CLI.
    """
    app = Flask("keeper")

    # Apply configuration
    if profile is None:
        # Let Python API clients (like pytest) set the profile directly
        # Otherwise, the profile is obtained from the shell environment.
        _profile = os.getenv("LTD_KEEPER_PROFILE", "development")
    else:
        _profile = profile
    app.config.from_object(config[_profile])
    config[_profile].init_app(app)

    # Add the middleware to respect headers forwarded from the proxy server
    # Assigning to the wsgi_app method is recommended by the Flask docs
    if app.config["PROXY_FIX"]:
        app.wsgi_app = ProxyFix(  # type: ignore [assignment]
            app.wsgi_app,
            x_for=app.config["TRUST_X_FOR"],
            x_proto=app.config["TRUST_X_PROTO"],
            x_host=app.config["TRUST_X_HOST"],
            x_port=app.config["TRUST_X_PORT"],
            x_prefix=app.config["TRUST_X_PREFIX"],
        )

    # Initialize the celery app
    from keeper.celery import create_celery_app

    create_celery_app(app)

    # Initialize the Flask-SQLAlchemy  database interface and
    # initialize Alembic migrations through Flask-Migrate
    from keeper.models import db, migrate

    db.init_app(app)
    migrate.init_app(
        app, db, compare_type=True, render_as_batch=True  # for autogenerate
    )  # for sqlite; safe for other servers

    # Register blueprints
    from keeper.apiroot import apiroot as apiroot_blueprint

    app.register_blueprint(apiroot_blueprint, url_prefix=None)

    if app.config["ENABLE_V1_API"]:
        from keeper.api import api as api_blueprint

        app.register_blueprint(api_blueprint, url_prefix=None)

    if app.config["ENABLE_V2_API"]:
        from keeper.v2api import v2api as v2api_blueprint

        app.register_blueprint(v2api_blueprint, url_prefix="/v2")

    # Add custom Flask CLI subcommands
    from keeper.cli import add_app_commands

    add_app_commands(app)

    return app
