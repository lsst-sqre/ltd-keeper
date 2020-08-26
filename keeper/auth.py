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

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import structlog
from flask import current_app, g, jsonify
from flask_httpauth import HTTPBasicAuth

from keeper.models import User

if TYPE_CHECKING:
    from flask import Response

__all__ = [
    "password_auth",
    "token_auth",
    "verify_password",
    "unauthorized",
    "verify_auth_token",
    "unauthorized",
    "verify_auth_token",
    "permission_required",
    "is_authorized",
]

password_auth = HTTPBasicAuth()
"""User+Password-based auth (only allowed for getting a token)."""

token_auth = HTTPBasicAuth()
"""Token-based auth (used for all requests)."""


@password_auth.verify_password
def verify_password(username: str, password: str) -> bool:
    """Verify a user's password corresponding to a username (for
    `password_auth` middleware).

    Parameters
    ----------
    username : `str`
        The user's username, as provided in the request.
    password : `str`
        The password provided in the request.

    Returns
    -------
    bool
        ``True`` if the password is valid and ``False`` otherwise (including
        if the user does not exist).

    Notes
    -----
    This middleware binds the user's username to the request logger.
    """
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
def unauthorized() -> Response:
    """Handle error response for `password_auth` middleware.

    Returns
    -------
    flask.Response
        Flask response (401 unauthorized status).
    """
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
def verify_auth_token(token: str, *args: Any) -> bool:
    """Verify an auth token (for `token_auth` middleware).

    Parameters
    ----------
    token : `str`
        The token, which takes the place of the "username" in basic auth.

    Returns
    -------
    bool
        ``True`` if the password is valid and ``False`` otherwise (including
        if the user does not exist).

    Notes
    -----
    This middleware binds the user's username to the request logger.
    """
    if current_app.config.get("IGNORE_AUTH"):
        # App is in a testing state; use the default user
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
def unauthorized_token() -> Response:
    """Handle error response for `password_auth` middleware.

    Returns
    -------
    flask.Response
        Flask response (401 unauthorized status).
    """
    response = jsonify(
        {
            "status": 401,
            "error": "unauthorized",
            "message": "please send your authentication token",
        }
    )
    response.status_code = 401
    return response


F = TypeVar("F", bound=Callable[..., Any])


def permission_required(permission: int) -> Callable[[F], F]:
    """Route decorator to test user authorizations.

    Examples
    --------
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

    def decorator(f):  # type: ignore
        @wraps(f)
        def decorated_function(*args, **kwargs):  # type: ignore
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


def is_authorized(permission: int) -> bool:
    """Test whether the current user has the given permission.

    Returns
    -------
    bool
        ``True`` if the current user in the request context has the current
        set of permissions based on `keeper.models.User.has_permission`.
    """
    if current_app.config.get("IGNORE_AUTH") is True:
        # App is in a testing state
        return True
    elif g.get("user", None) is None:
        # User not authenticated
        return False
    else:
        return g.user.has_permission(permission)
