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

    SERVER_NAME = 'testing.io'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' \
        + os.path.join(BASEDIR, 'ltd-keeper-test.sqlite')
    SERVER_NAME = 'testing.io'

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
