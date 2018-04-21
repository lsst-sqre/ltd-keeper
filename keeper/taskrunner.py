"""Convenience APIs for launching Celery task queues.
"""

__all__ = ('append_task_to_chain', 'launch_task_chain')

import celery
from flask import g
import structlog


def append_task_to_chain(task_signature):
    """Append a task to the to the task chain of this request.

    Parameters
    ----------
    task_signature : `celery.Signature`
        Celery task signature. Use an immutable signature, ``task.si()`` if
        the Task does not expect to recieve the result of the prior task.
    """
    logger = structlog.get_logger(__name__)

    if 'tasks' not in g:
        g.tasks = []

    g.tasks.append(task_signature)

    logger.info('Queued celery task', task=str(task_signature))


def launch_task_chain():
    """Launch the celery tasks attached to the application context
    (``flask.g``) of this request.
    """
    logger = structlog.get_logger(__name__)

    if 'tasks' not in g or len(g.tasks) == 0:
        logger.debug('Did not launch any tasks',
                     ntasks=0)
        return

    logger.info('Launching task chain',
                ntasks=len(g.tasks),
                tasks=str(g.tasks))
    celery.chain(*g.tasks).apply_async()

    # Reset the queued task signatures
    g.tasks = []
