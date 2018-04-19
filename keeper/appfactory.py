"""Flask application factory.

Applies configurations, creates the DB schema (if necessary) and registers
all HTTP routes.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

__all__ = ('create_flask_app',)

import os

from flask import Flask, jsonify, g

from .config import config
from .logutils import log_route


def create_flask_app(profile=None):
    """Create an application instance.

    This is called by a runner script, such as /run.py.
    """

    from .auth import password_auth

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

    # authentication token route
    @app.route('/token')
    @log_route()
    @password_auth.login_required
    def get_auth_token():
        """Obtain a token for API users.

        **Example request**

        .. code-block:: http

           GET /token HTTP/1.1
           Accept: */*
           Accept-Encoding: gzip, deflate
           Authorization: Basic dXNlcjpwYXNz
           Connection: keep-alive
           Host: localhost:5000
           User-Agent: HTTPie/0.9.3

        **Example response**

        .. code-block:: http

           HTTP/1.0 200 OK
           Content-Length: 139
           Content-Type: application/json
           Date: Tue, 09 Feb 2016 20:23:11 GMT
           Server: Werkzeug/0.11.3 Python/3.5.0

           {
               "token": "eyJhbGciOiJIUzI1NIsImlhdCI6MTQ1NTA0OTM5MSwiZXhwIjo..."
           }

        :reqheader Authorization: ``username:password``

        :>json string token: Token string. Use this token in the basic auth
           ``username`` field.

        :statuscode 200: No errors.
        :statuscode 401: Not authenticated.
        """
        return jsonify({'token': g.user.generate_auth_token()})

    return app
