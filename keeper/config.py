"""ltd-keeper configuration and environment profiles."""

import abc
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """Configuration baseclass."""

    __metaclass__ = abc.ABCMeta

    SECRET_KEY = 'secret-key'
    DEBUG = False
    IGNORE_AUTH = False
    PREFERRED_URL_SCHEME = 'http'
    AWS_ID = os.environ.get('LTD_KEEPER_AWS_ID')
    AWS_SECRET = os.environ.get('LTD_KEEPER_AWS_SECRET')
    FASTLY_KEY = os.environ.get('LTD_KEEPER_FASTLY_KEY')
    FASTLY_SERVICE_ID = os.environ.get('LTD_KEEPER_FASTLY_ID')
    LTD_DASHER_URL = os.getenv('LTD_DASHER_URL', None)

    # Suppresses a warning until Flask-SQLAlchemy 3
    # See http://stackoverflow.com/a/33790196
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @abc.abstractclassmethod
    def init_app(cls, app):
        pass


class DevelopmentConfig(Config):
    """Local development configuration."""

    DEBUG = True
    IGNORE_AUTH = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('LTD_KEEPER_DEV_DB_URL') or \
        'sqlite:///' + os.path.join(BASEDIR, 'ltd-keeper-dev.sqlite')
    DEFAULT_USER = 'user'
    DEFAULT_PASSWORD = 'pass'

    @classmethod
    def init_app(cls, app):
        """Initialization hook called during create_app."""
        pass


class TestConfig(Config):
    """Test configuration (for py.test harness)."""

    SERVER_NAME = 'example.test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' \
        + os.path.join(BASEDIR, 'ltd-keeper-test.sqlite')

    @classmethod
    def init_app(cls, app):
        """Initialization hook called during create_app."""
        pass


class ProductionConfig(Config):
    """Production configuration."""

    SECRET_KEY = os.environ.get('LTD_KEEPER_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('LTD_KEEPER_DB_URL')
    DEFAULT_USER = os.environ.get('LTD_KEEPER_BOOTSTRAP_USER')
    DEFAULT_PASSWORD = os.environ.get('LTD_KEEPER_BOOTSTRAP_PASSWORD')
    PREFERRED_URL_SCHEME = os.environ.get('LTD_KEEPER_URL_SCHEME')

    @classmethod
    def init_app(cls, app):
        """Initialization hook called during create_app."""
        pass


config = {
    'development': DevelopmentConfig,
    'testing': TestConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
