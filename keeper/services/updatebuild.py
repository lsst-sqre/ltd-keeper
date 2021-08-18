"""Update a build resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.models import db

if TYPE_CHECKING:
    from keeper.models import Build


def update_build(*, build: Build, uploaded: Optional[bool]) -> Build:
    """Update a build resource, including indicating that it is uploaded.

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
    if uploaded is True:
        build.register_uploaded_build()

    db.session.add(build)
    db.session.commit()

    return build
