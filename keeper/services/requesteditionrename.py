"""This services launches a task to rename an edition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.taskrunner import queue_task_command

if TYPE_CHECKING:
    from keeper.models import Edition

__all__ = ["request_edition_rename"]


def request_edition_rename(*, edition: Edition, slug: str) -> Edition:
    queue_task_command(
        command="rename_edition",
        data={"edition_id": edition.id, "slug": slug},
    )
    return edition
