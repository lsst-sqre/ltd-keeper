"""ltd-keeper configuration and environment profiles."""

import abc
import logging
import os
import sys

import structlog

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
"""Director path at the root of the repository (only for test and development
profiles).
"""


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
    CELERY_RESULT_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    LTD_EVENTS_URL = os.getenv('LTD_EVENTS_URL', None)

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
        """Initialization hook called during
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        logger = logging.getLogger('keeper')
        logger.addHandler(stream_handler)
        logger.setLevel(logging.DEBUG)

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                # structlog.stdlib.render_to_log_kwargs,
                structlog.processors.KeyValueRenderer(
                    key_order=["event", "method", "path", "request_id"],
                ),
            ],
            context_class=structlog.threadlocal.wrap_dict(dict),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


class TestConfig(Config):
    """Test configuration (for py.test harness)."""

    SERVER_NAME = 'example.test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' \
        + os.path.join(BASEDIR, 'ltd-keeper-test.sqlite')

    @classmethod
    def init_app(cls, app):
        """Initialization hook called during `
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        logger = logging.getLogger('keeper')
        logger.addHandler(stream_handler)
        logger.setLevel(logging.DEBUG)

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                # structlog.stdlib.render_to_log_kwargs,
                structlog.processors.KeyValueRenderer(
                    key_order=["event", "method", "path", "request_id"],
                ),
            ],
            context_class=structlog.threadlocal.wrap_dict(dict),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


class ProductionConfig(Config):
    """Production configuration."""

    SECRET_KEY = os.environ.get('LTD_KEEPER_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('LTD_KEEPER_DB_URL')
    DEFAULT_USER = os.environ.get('LTD_KEEPER_BOOTSTRAP_USER')
    DEFAULT_PASSWORD = os.environ.get('LTD_KEEPER_BOOTSTRAP_PASSWORD')
    PREFERRED_URL_SCHEME = os.environ.get('LTD_KEEPER_URL_SCHEME')

    @classmethod
    def init_app(cls, app):
        """Initialization hook called during
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        logger = logging.getLogger('keeper')
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=structlog.threadlocal.wrap_dict(dict),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


config = {
    'development': DevelopmentConfig,
    'testing': TestConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
