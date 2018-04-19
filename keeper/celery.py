"""Factory for the Celery application.
"""

__all__ = ('celery_app', 'create_celery_app')

from celery import Celery


celery_app = None
"""Celery app instance, initialized by `create_celery_app` via
`keeper.appfactory.create_flask_app`.
"""


def create_celery_app(flask_app):
    """Create the Celery app.

    This implementation is based on
    http://flask.pocoo.org/docs/0.12/patterns/celery/ to leverage the
    Flask config to also configure Celery.
    """
    global celery_app
    celery_app = Celery(flask_app.import_name,
                        backend=flask_app.config['CELERY_RESULT_URL'],
                        broker=flask_app.config['CELERY_BROKER_URL'])
    celery_app.conf.update(flask_app.config)
    TaskBase = celery_app.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery_app.Task = ContextTask
