"""Convenience APIs for launching Celery task queues."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import celery
import structlog
from flask import current_app, g

from keeper.tasks.registry import task_registry

__all__ = [
    "queue_task_command",
    "launch_tasks",
]


def queue_task_command(command: str, data: Dict[str, Any]) -> Any:
    """Queue a celergy task command."""
    if "task_commands" not in g:
        g.task_commands = []

    g.task_commands.append((command, data))


def launch_tasks() -> celery.chain:
    """Launch the celery tasks attached to the application context
    (``flask.g``) of this request.
    """
    logger = structlog.get_logger(__name__)

    if "task_commands" in g:
        task_commands = _order_tasks(g.task_commands)
    else:
        task_commands = []

    inspect_task_queue(task_commands)

    if len(task_commands) == 0:
        logger.debug("Did not launch any tasks", ntasks=0)
        return

    if not current_app.config["ENABLE_TASKS"]:
        logger.debug("Celery taks are disabled")
        return

    celery_task_signatures: List[celery.Signature] = []
    for task_name, task_data in task_commands:
        task_function = task_registry[task_name].task
        celery_task_signatures.append(task_function.si(**task_data))

    chain = celery.chain(*celery_task_signatures).apply_async()
    logger.info(
        "Launching task chain",
        ntasks=len(task_commands),
        tasks=task_commands,
        task_id=chain.id,
    )

    # Reset the queued task signatures
    g.tasks = []

    return chain


def _order_tasks(
    task_commands: List[Tuple[str, Dict[str, Any]]]
) -> List[Tuple[str, Dict[str, Any]]]:
    # TODO implement this method to re-order and de-duplicate tasks
    return task_commands


def inspect_task_queue(
    task_commands: List[Tuple[str, Dict[str, Any]]]
) -> None:
    """A no-op function that can be mocked to inspect what tasks will be run
    by ``launch_tasks``.
    """
    pass
