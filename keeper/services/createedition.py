from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from keeper.models import Edition, db
from keeper.taskrunner import append_task_to_chain, mock_registry
from keeper.tasks.dashboardbuild import build_dashboard

if TYPE_CHECKING:
    from keeper.models import Product


# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.services.createedition.append_task_to_chain",
    ]
)


def create_edition(
    *,
    product: Product,
    title: str,
    tracking_mode: Optional[str] = None,
    slug: Optional[str] = None,
    autoincrement_slug: bool = False,
    tracked_ref: str = "master",
    build_url: Optional[str] = None,
) -> Edition:
    """Create a new edition.

    The edition is added to the current database session. A dashboard rebuild
    task is also appended to the task chain. The caller is responsible for
    committing the database session and launching the celery task.

    Parameters
    ----------
    product : `keeper.models.Product`
        The product that owns this edition.
    tracking_mode : str, optional
        The string name of the edition's tracking mode. If left None,
        defaults to `keeper.models.Edition.default_mode_name`.
    slug : str, optional
        The URL-safe slug for this edition. Can be `None` if
        ``autoincrement_slug`` is True.
    title : str
        The human-readable title.
    autoincrement_slug : bool
        If True, rather then use the provided ``slug``, the slug is an
        integer that is incremented by one from the previously-existing integer
        slug.
    tracked_ref : str, optional
        The name of the Git ref that this edition tracks, if ``tracking_mode``
        is ``"git_refs"``.
    build_url : str, optional
        The URL of the build to initially publish with this edition.

    Returns
    -------
    edition : `keeper.models.Edition`
        The edition, which is also added to the current database session.
    """
    edition = Edition(product=product, surrogate_key=uuid.uuid4().hex)

    if autoincrement_slug:
        edition.slug = edition._compute_autoincremented_slug()
        edition.title = edition.slug
    else:
        edition.slug = slug
        edition.title = title
    assert isinstance(edition.slug, str)  # for type checking
    edition._validate_slug(edition.slug)

    if tracking_mode is not None:
        edition.set_mode(tracking_mode)
    else:
        edition.set_mode(edition.default_mode_name)

    if edition.mode_name == "git_refs":
        edition.tracked_refs = [tracked_ref]

    if build_url is not None:
        # FIXME refactor this into a service.
        edition.set_pending_rebuild(build_url)

    db.session.add(edition)

    append_task_to_chain(build_dashboard.si(product.id))

    return edition
