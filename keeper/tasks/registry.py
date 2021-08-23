"""Celery task registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict

from .dashboardbuild import build_dashboard
from .editionrebuild import mock_rebuild_edition, rebuild_edition
from .renameedition import mock_rename_edition, rename_edition

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

    test_mock: Callable
    """A function that performs the DB actions of a task without its other
    side-effects.
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
        self,
        *,
        name: str,
        task: celery.app.task.Task,
        order: int,
        test_mock: Callable,
    ) -> None:
        """Add a task to the registry."""
        self._tasks[name] = RegisteredTask(
            name=name, task=task, order=order, test_mock=test_mock
        )


task_registry = TaskRegistry()

task_registry.add(
    name="rename_editon",
    task=rename_edition,
    order=9,
    test_mock=mock_rename_edition,
)

task_registry.add(
    name="rebuild_edition",
    task=rebuild_edition,
    order=10,
    test_mock=mock_rebuild_edition,
)

task_registry.add(
    name="build_dashboard",
    task=build_dashboard,
    order=20,
    test_mock=lambda product_id: None,
)
