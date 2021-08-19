from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from keeper.models import Edition, db

from .request_dashboard_build import request_dashboard_build
from .requesteditionrebuild import request_edition_rebuild

if TYPE_CHECKING:
    from keeper.models import Build, Product


def create_edition(
    *,
    product: Product,
    title: str,
    tracking_mode: Optional[str] = None,
    slug: Optional[str] = None,
    autoincrement_slug: bool = False,
    tracked_ref: str = "master",
    build: Optional[Build] = None,
) -> Edition:
    """Create a new edition.

    The edition is added to the current database session and comitted.
    A dashboard rebuild task is also appended to the task chain. The caller is
    responsible for launching the celery task.

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
    build : Build, optional
        The build to initially publish with this edition.

    Returns
    -------
    edition : `keeper.models.Edition`
        The edition, which is also added to the current database session.
    """
    edition = Edition(
        product=product, surrogate_key=uuid.uuid4().hex, pending_rebuild=False
    )

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

    db.session.add(edition)
    db.session.commit()

    if build is not None:
        request_edition_rebuild(edition=edition, build=build)

    request_dashboard_build(product)

    return edition
