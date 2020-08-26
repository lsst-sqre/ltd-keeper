"""Factory for the Celery application."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from celery import Celery

if TYPE_CHECKING:
    from flask import Flask

__all__ = ["celery_app", "create_celery_app"]

celery_app: Any = None
"""Celery app instance, initialized by `create_celery_app` via
`keeper.appfactory.create_flask_app`.
"""


def create_celery_app(flask_app: Flask) -> None:
    """Create the Celery app.

    This implementation is based on
    http://flask.pocoo.org/docs/0.12/patterns/celery/ to leverage the
    Flask config to also configure Celery.
    """
    global celery_app
    celery_app = Celery(
        flask_app.import_name,
        backend=flask_app.config["CELERY_RESULT_URL"],
        broker=flask_app.config["CELERY_BROKER_URL"],
        task_track_started=True,
    )
    celery_app.conf.update(flask_app.config)
    TaskBase = celery_app.Task

    class ContextTask(TaskBase):  # type: ignore
        abstract = True

        def __call__(self, *args, **kwargs):  # type: ignore
            with flask_app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery_app.Task = ContextTask

    # Ensure that all tasks are import and registered before they're called
    # For example, rebuild_edition's import is deferred otherwise in
    # keeper.models to avoid circular imports
    from . import tasks  # noqa: F401
