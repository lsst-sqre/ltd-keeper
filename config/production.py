"""Production mode configurations for ltd-keeper.

This configurations are used by the run.py script.
"""

import os


def _cast_envvar_bool(var_name, default=False):
    token = os.getenv(var_name, default=default)
    if token in ['True', 'true', 'TRUE', True]:
        return True
    elif token in ['False', 'false', 'FALSE', False]:
        return False
    else:
        raise ValueError('Could not parse configuration {0}={1}'.format(
            var_name, token))


def _required_envvar(var_name):
    token = os.getenv(var_name, default=None)
    if token is None:
        raise ValueError('Missing environment variable: {0}'.format(var_name))
    return token


DEBUG = _cast_envvar_bool('LTD_KEEPER_DEBUG', default=False)
IGNORE_AUTH = _cast_envvar_bool('LTD_KEEPER_IGNORE_AUTH', default=False)
SECRET_KEY = _required_envvar('LTD_KEEPER_SECRET_KEY')
SQLALCHEMY_DATABASE_URI = _required_envvar('LTD_KEEPER_DB_URI')
DEFAULT_USER = _required_envvar('LTD_KEEPER_DEFAULT_USER')
DEFAULT_PASSWORD = _required_envvar('LTD_KEEPER_DEFAULT_PASSWORD')
