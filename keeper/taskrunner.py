"""Convenience APIs for launching Celery task queues."""

from __future__ import annotations

import collections
from typing import Any, Dict, List, Optional

import celery
import structlog
from flask import g, url_for

__all__ = [
    "append_task_to_chain",
    "launch_task_chain",
    "insert_task_url_in_response",
    "mock_registry",
]


def append_task_to_chain(task_signature: celery.Signature) -> None:
    """Append a task to the to the task chain of this request.

    Parameters
    ----------
    task_signature : `celery.Signature`
        Celery task signature. Use an immutable signature, ``task.si()`` if
        the Task does not expect to recieve the result of the prior task.
    """
    logger = structlog.get_logger(__name__)

    if "tasks" not in g:
        g.tasks = []

    g.tasks.append(task_signature)

    logger.info("Queued celery task", task=str(task_signature))


def launch_task_chain() -> celery.chain:
    """Launch the celery tasks attached to the application context
    (``flask.g``) of this request.
    """
    logger = structlog.get_logger(__name__)

    if "tasks" not in g or len(g.tasks) == 0:
        logger.debug("Did not launch any tasks", ntasks=0)
        return

    chain = celery.chain(*g.tasks).apply_async()
    logger.info(
        "Launching task chain",
        ntasks=len(g.tasks),
        tasks=str(g.tasks),
        task_id=chain.id,
    )

    # Reset the queued task signatures
    g.tasks = []

    return chain


def insert_task_url_in_response(
    json_data: Dict[str, Any], task: Optional[celery.Task]
) -> Dict[str, Any]:
    """Insert the task status URL into the JSON response body."""
    if task is not None:
        url = url_for("api.get_task_status", id=task.id, _external=True)
        json_data["queue_url"] = url
    return json_data


class MockRegistry(collections.UserList):
    """Registry of celery task runner API imports that should be mocked."""

    def __init__(self, data: Optional[List[Any]] = None) -> None:
        if data:
            self.data = data
        else:
            self.data = []

        self._mocks: Dict[str, Any] = {}

    def __getitem__(self, name: Any) -> Any:
        return self._mocks[name]

    def patch_all(self, mocker: Any) -> None:
        """Apply ``mocker.patch`` to each registered import."""
        for name in self.data:
            self._mocks[name] = mocker.patch(name)


mock_registry = MockRegistry()
"""Instance of `MockRegistry`.

All imports of `append_task_to_chain` and `launch_task_chain` need to be
registed in this instance.

Example for a module named ``mymodule``::

    from keeper.taskrunner import append_task_to_chain, mock_registry

    mock_registry.append('keeper.mymodule.append_task_to_chain')
"""
