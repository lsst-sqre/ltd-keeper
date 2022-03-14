"""Authentication routes."""

from __future__ import annotations

from flask import g
from flask_accept import accept_fallback

from keeper.apiroot import apiroot
from keeper.auth import password_auth
from keeper.logutils import log_route

from ._models import AuthTokenResponse


@apiroot.route("/token")
@accept_fallback
@log_route()
@password_auth.login_required
def get_auth_token() -> str:
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
    return AuthTokenResponse(token=g.user.generate_auth_token()).json()
