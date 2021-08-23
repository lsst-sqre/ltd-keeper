"""ltd-keeper configuration and environment profiles."""

from __future__ import annotations

import abc
import logging
import os
import sys
from typing import TYPE_CHECKING, Dict, Optional, Type

import structlog

from keeper.models import EditionKind

if TYPE_CHECKING:
    from flask import Flask

__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestConfig",
    "ProductionConfig",
    "config",
]

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
"""Director path at the root of the repository (only for test and development
profiles).
"""


class Config(abc.ABC):
    """Configuration baseclass."""

    SECRET_KEY: Optional[str] = "secret-key"
    DEBUG: bool = False
    IGNORE_AUTH: bool = False
    PREFERRED_URL_SCHEME: str = "http"
    AWS_ID: Optional[str] = os.environ.get("LTD_KEEPER_AWS_ID")
    AWS_SECRET: Optional[str] = os.environ.get("LTD_KEEPER_AWS_SECRET")
    FASTLY_KEY: Optional[str] = os.environ.get("LTD_KEEPER_FASTLY_KEY")
    FASTLY_SERVICE_ID: Optional[str] = os.environ.get("LTD_KEEPER_FASTLY_ID")
    LTD_DASHER_URL: Optional[str] = os.getenv("LTD_DASHER_URL", None)
    CELERY_RESULT_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    LTD_EVENTS_URL: Optional[str] = os.getenv("LTD_EVENTS_URL", None)
    DEFAULT_EDITION_KIND: EditionKind = EditionKind.draft

    ENABLE_V1_API: bool = bool(int(os.getenv("LTD_KEEPER_ENABLE_V1", "1")))
    ENABLE_V2_API: bool = bool(int(os.getenv("LTD_KEEPER_ENABLE_V2", "1")))

    # Suppresses a warning until Flask-SQLAlchemy 3
    # See http://stackoverflow.com/a/33790196
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    PROXY_FIX: bool = bool(int(os.getenv("LTD_KEEPER_PROXY_FIX", "0")))
    """Activate the Werkzeug ProxyFix middleware by setting to 1.

    Only activate this middleware when LTD Keeper is deployed behind a
    trusted proxy.

    Related configurations:

    - ``TRUST_X_FOR``
    - ``TRUST_X_PROTO``
    - ``TRUST_X_HOST``
    - ``TRUST_X_PORT``
    - ``TRUST_X_PREFIX``
    """

    TRUST_X_FOR: int = int(os.getenv("LTD_KEEPER_X_FOR", "1"))
    """Number of values to trust for X-Forwarded-For."""

    TRUST_X_PROTO: int = int(os.getenv("LTD_KEEPER_X_PROTO", "1"))
    """Number of values to trust for X-Forwarded-Proto."""

    TRUST_X_HOST: int = int(os.getenv("LTD_KEEPER_X_HOST", "1"))
    """Number of values to trust for X-Forwarded-Host."""

    TRUST_X_PORT: int = int(os.getenv("LTD_KEEPER_X_PORT", "0"))
    """Number of values to trust for X-Forwarded-Port."""

    TRUST_X_PREFIX: int = int(os.getenv("LTD_KEEPER_X_PREFIX", "0"))
    """Number of values to trust for X-Forwarded-Prefix."""

    ENABLE_TASKS: bool = bool(int(os.getenv("LTD_KEEPER_ENABLE_TASKS", "1")))

    @abc.abstractclassmethod
    def init_app(cls, app: Flask) -> None:
        pass


class DevelopmentConfig(Config):
    """Local development configuration."""

    DEBUG = True
    IGNORE_AUTH = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "LTD_KEEPER_DEV_DB_URL"
    ) or "sqlite:///" + os.path.join(BASEDIR, "ltd-keeper-dev.sqlite")
    DEFAULT_USER = "user"
    DEFAULT_PASSWORD = "pass"

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Initialization hook called during
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("keeper")
        if logger.hasHandlers():
            logger.handlers.clear()
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

    SERVER_NAME = "example.test"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "LTD_KEEPER_TEST_DB_URL"
    ) or "sqlite:///" + os.path.join(BASEDIR, "ltd-keeper-test.sqlite")
    ENABLE_TASKS = False

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Initialization hook called during `
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("keeper")
        if logger.hasHandlers():
            logger.handlers.clear()
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

    SECRET_KEY = os.environ.get("LTD_KEEPER_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("LTD_KEEPER_DB_URL")
    DEFAULT_USER = os.environ.get("LTD_KEEPER_BOOTSTRAP_USER")
    DEFAULT_PASSWORD = os.environ.get("LTD_KEEPER_BOOTSTRAP_PASSWORD")
    PREFERRED_URL_SCHEME = os.environ.get("LTD_KEEPER_URL_SCHEME", "https")

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Initialization hook called during
        `keeper.appfactory.create_flask_app`.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("keeper")
        logger.addHandler(stream_handler)
        if logger.hasHandlers():
            logger.handlers.clear()
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


config: Dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}
