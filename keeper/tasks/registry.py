"""Celery task registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from .dashboardbuild import build_dashboard
from .editionrebuild import rebuild_edition

if TYPE_CHECKING:
    import celery.app.task.Task

__all__ = ["TaskRegistry", "task_registry", "RegisteredTask"]


@dataclass
class RegisteredTask:
    """A celery task with metadata."""

    name: str
    """The task's identifier."""

    task: celery.app.task.Task
    """The task function."""

    order: int
    """The sorting order of the task; tasks with smaller sort orders run
    first.
    """

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, RegisteredTask):
            return self.order < other.order
        else:
            raise ValueError

    def __le__(self, other: Any) -> bool:
        if isinstance(other, RegisteredTask):
            return self.order <= other.order
        else:
            raise ValueError

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, RegisteredTask):
            return self.order >= other.order
        else:
            raise ValueError

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, RegisteredTask):
            return self.order > other.order
        else:
            raise ValueError


class TaskRegistry:
    """A registry that associates task command names with their
    Celery callable functions.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, RegisteredTask] = {}

    def __getitem__(self, name: str) -> RegisteredTask:
        return self._tasks[name]

    def add(
        self, *, name: str, task: celery.app.task.Task, order: int
    ) -> None:
        """Add a task to the registry."""
        self._tasks[name] = RegisteredTask(name=name, task=task, order=order)


task_registry = TaskRegistry()

task_registry.add(
    name="rebuild_edition",
    task=rebuild_edition,
    order=10,
)

task_registry.add(name="build_dashboard", task=build_dashboard, order=20)
