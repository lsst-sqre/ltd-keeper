"""Update a build resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.models import db
from keeper.taskrunner import append_task_to_chain, mock_registry
from keeper.tasks.dashboardbuild import build_dashboard

if TYPE_CHECKING:
    from keeper.models import Build


# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.services.updatebuild.append_task_to_chain",
    ]
)


def update_build(*, build: Build, uploaded: Optional[bool]) -> Build:
    """Update a build resource, including indicating that it is uploaded.

    This method adds the build to the database session.

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

    append_task_to_chain(build_dashboard.si(build.product.id))

    return build
