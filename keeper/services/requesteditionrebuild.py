"""This service requests a rebuild requestion for an edition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from structlog import get_logger

from keeper.exceptions import ValidationError
from keeper.taskrunner import queue_task_command

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["request_edition_rebuild"]


def request_edition_rebuild(*, edition: Edition, build: Build) -> Edition:
    logger = get_logger(__name__)
    logger.info(
        "Starting request_edition_rebuild",
        edition=edition.slug,
        build=build.slug,
    )

    # if edition.pending_rebuild:
    #     raise ValidationError(
    #         "This edition already has a pending rebuild, this request "
    #         "will not be accepted."
    #     )
    if build.uploaded is False:
        raise ValidationError(f"Build has not been uploaded: {build.slug}")
    if build.date_ended is not None:
        raise ValidationError(f"Build was deprecated: {build.slug}")

    # Update edition with new state
    # edition.build = build  # FIXME move this to the task?
    # edition.pending_rebuild = True  # FIXME move this to the task?

    queue_task_command(
        command="rebuild_edition",
        data={"edition_id": edition.id, "build_id": build.id},
    )

    return edition
