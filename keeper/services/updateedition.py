"""A service for updating an edition, including its metadata or pointing to
a new build.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from structlog import get_logger

from keeper.models import db
from keeper.taskrunner import append_task_to_chain, mock_registry
from keeper.tasks.dashboardbuild import build_dashboard

if TYPE_CHECKING:
    from keeper.models import Edition


# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.services.updateedition.append_task_to_chain",
    ]
)


def update_edition(
    *,
    edition: Edition,
    build_url: Optional[str] = None,
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

    if build_url is not None:
        edition.set_pending_rebuild(build_url=build_url)

    if slug is not None:
        edition.update_slug(slug)

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

    append_task_to_chain(build_dashboard.si(product.id))

    return edition
