"""Update a build resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import structlog

from keeper.models import db

from .updateedition import update_edition

if TYPE_CHECKING:
    from keeper.models import Build


def update_build(*, build: Build, uploaded: Optional[bool]) -> Build:
    """Update a build resource, including indicating that it is uploaded,
    and trigger rebuilds for tracking editions.

    This method adds the build to the database session and commits it.

    Parameters
    ----------
    build : `keeper.models.Build`
        Build model.
    uploaded : `bool`, optional
        Flag indicating if the build is uploaded or not.

    Returns
    -------
    build : `keeper.models.Build`
        Build model.
    """
    logger = structlog.get_logger(__name__)
    logger.info("Updating build", build=build.slug, uploaded=uploaded)

    if uploaded is True:
        build.register_uploaded_build()
        db.session.add(build)
        db.session.commit()

        editions_to_rebuild = build.get_tracking_editions()
        for edition in editions_to_rebuild:
            update_edition(edition=edition, build=build)

    return build
