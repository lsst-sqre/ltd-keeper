"""Helper functions for password and token-based authentication
using :mod:`flask.ext.httpauth` and user authorization.

To apply password-based auth to a route, use the
`@password_auth.login_required` decorator; use `@token_auth.login

Use the following decorators to apply authentication to any route:

- `@password_auth.login_required` for password auth (only use to GET a token).
- `@token_auth.login_required` for token (for all other authenticated routes).

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

from functools import wraps

import structlog
from flask import current_app, g, jsonify
from flask_httpauth import HTTPBasicAuth

from .models import User

# User+Password-based auth (only allowed for getting a token)
password_auth = HTTPBasicAuth()

# Token-based auth (used for all requests)
token_auth = HTTPBasicAuth()


@password_auth.verify_password
def verify_password(username, password):
    g.user = User.query.filter_by(username=username).first()

    # Bind the username to the logger
    if g.user is not None:
        structlog.get_logger().bind(username=g.user.username)
    else:
        structlog.get_logger().bind(username=None)

    if g.user is None:
        return False

    return g.user.verify_password(password)


@password_auth.error_handler
def unauthorized():
    response = jsonify(
        {
            "status": 401,
            "error": "unauthorized",
            "message": "please authenticate",
        }
    )
    response.status_code = 401
    return response


@token_auth.verify_password
def verify_auth_token(token, unused):
    if current_app.config.get("IGNORE_AUTH") is True:
        g.user = User.query.get(1)
    else:
        g.user = User.verify_auth_token(token)

    # Bind the username to the logger
    if g.user is not None:
        structlog.get_logger().bind(username=g.user.username)
    else:
        structlog.get_logger().bind(username=None)

    return g.user is not None


@token_auth.error_handler
def unauthorized_token():
    response = jsonify(
        {
            "status": 401,
            "error": "unauthorized",
            "message": "please send your authentication token",
        }
    )
    response.status_code = 401
    return response


def permission_required(permission):
    """Route decorator to test user authorizations.

    The decorator should be applied *after* the authentication decorator.
    For example::

        @api.route('/secure')
        @auth.permission_required(Permission.ADMIN_USER)
        @token_auth.login_required
        def hello():
            pass

    Response with a 403 response if authorization fails. If the user is
    not set (because the username/password was blank, or because a
    token_required decorator was not applied, then a 401 response is sent.
    Authorization requires authentication.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_app.config.get("IGNORE_AUTH") is True:
                return f(*args, **kwargs)
            elif g.get("user", None) is None:
                # user not authenticated
                response = jsonify(
                    {
                        "status": 401,
                        "error": "unauthenticated",
                        "message": "please authenticate",
                    }
                )
                response.status_code = 401
                return response
            elif not g.user.has_permission(permission):
                # user not authorized
                response = jsonify(
                    {
                        "status": 403,
                        "error": "unauthorized",
                        "message": "not authorized",
                    }
                )
                response.status_code = 403
                return response
            else:
                # user is authenticated+authorized
                return f(*args, **kwargs)

        return decorated_function

    return decorator


def is_authorized(permission):
    """Function is test whether a user has permission or not."""
    if current_app.config.get("IGNORE_AUTH") is True:
        return True
    elif g.get("user", None) is None:
        # user not authenticated
        return False
    else:
        return g.user.has_permission(permission)
