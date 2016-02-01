"""Helper functions for password and token-based authentication
using :mod:`flask.ext.httpauth`.

To apply password-based auth to a route, use the
`@password_auth.login_required` decorator; use `@token_auth.login

Use the following decorators to apply authentication to any route:

- `@password_auth.login_required` for password auth (only use to GET a token).
- `@token_auth.login_required` for token (for all other authenticated routes).
"""

from flask import jsonify, g, current_app
from flask.ext.httpauth import HTTPBasicAuth
from .models import User

# User+Password-based auth (only allowed for getting a token)
password_auth = HTTPBasicAuth()

# Token-based auth (used for all requests)
token_auth = HTTPBasicAuth()


@password_auth.verify_password
def verify_password(username, password):
    g.user = User.query.filter_by(username=username).first()
    if g.user is None:
        return False
    return g.user.verify_password(password)


@password_auth.error_handler
def unauthorized():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'please authenticate'})
    response.status_code = 401
    return response


@token_auth.verify_password
def verify_auth_token(token, unused):
    if current_app.config.get('IGNORE_AUTH') is True:
        g.user = User.query.get(1)
    else:
        g.user = User.verify_auth_token(token)
    return g.user is not None


@token_auth.error_handler
def unauthorized_token():
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': 'please send your authentication token'})
    response.status_code = 401
    return response
