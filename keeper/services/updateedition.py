"""A service for updating an edition, including its metadata or pointing to
a new build.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from structlog import get_logger

from keeper.models import db
from keeper.taskrunner import queue_task_command

from .requesteditionrebuild import request_edition_rebuild
from .requesteditionrename import request_edition_rename

if TYPE_CHECKING:
    from keeper.models import Build, Edition


def update_edition(
    *,
    edition: Edition,
    build: Optional[Build] = None,
    title: Optional[str] = None,
    slug: Optional[str] = None,
    tracking_mode: Optional[str] = None,
    tracked_ref: Optional[str] = None,
    pending_rebuild: Optional[bool] = None,
) -> Edition:
    """Update the metadata of an existing edititon or to point at a new
    build.
    """
    logger = get_logger(__name__)

    if tracked_ref is not None:
        edition.tracked_refs = [tracked_ref]

    if tracking_mode is not None:
        edition.set_mode(tracking_mode)

    if title is not None:
        edition.title = title

    if slug is not None:
        request_edition_rename(edition=edition)

    product = edition.product

    if pending_rebuild is not None:
        logger.warning(
            "Manual reset of Edition.pending_rebuild",
            edition_slug=edition.slug,
            project_slug=product.slug,
            prev_pending_rebuild=edition.pending_rebuild,
            new_pending_rebuild=pending_rebuild,
        )
        edition.pending_rebuild = pending_rebuild

    db.session.add(edition)
    db.session.commit()

    if build is not None:
        request_edition_rebuild(edition=edition, build=build)

    queue_task_command(
        command="build_dashboard", data={"product_id": product.id}
    )

    return edition
