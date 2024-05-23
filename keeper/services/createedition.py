from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING, Optional

from keeper.models import Edition, db

from .requestdashboardbuild import request_dashboard_build
from .requesteditionrebuild import request_edition_rebuild

if TYPE_CHECKING:
    from keeper.models import Build, Product


def create_edition(
    *,
    product: Product,
    title: Optional[str],
    tracking_mode: Optional[str] = None,
    slug: Optional[str] = None,
    autoincrement_slug: Optional[bool] = False,
    tracked_ref: Optional[str] = "main",
    build: Optional[Build] = None,
    kind: Optional[str] = None,
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
        The human-readable title; can be None if ``autoincrement_slug`` is
        True.
    autoincrement_slug : bool
        If True, rather then use the provided ``slug``, the slug is an
        integer that is incremented by one from the previously-existing integer
        slug.
    tracked_ref : str, optional
        The name of the Git ref that this edition tracks, if ``tracking_mode``
        is ``"git_refs"`` or ``"git_ref"``.
    build : Build, optional
        The build to initially publish with this edition.
    kind : str, optional
        The kind of the edition.

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

    # Set both tracked_ref and tracked_refs for the purposes of the migration
    # for now
    if edition.mode_name == "git_refs":
        edition.tracked_refs = [tracked_ref]
        edition.tracked_ref = tracked_ref
    elif edition.mode_name == "git_ref":
        edition.tracked_ref = tracked_ref
        edition.tracked_refs = [tracked_ref]

    if edition.slug == "__main":
        # Always mark the default edition as the main edition
        edition.set_kind("main")
    elif kind is not None:
        # Manually set the edition kind
        edition.set_kind(kind)
    elif tracked_ref is not None:
        # Set the EditionKind based on the tracked_ref value
        edition.set_kind(determine_edition_kind(tracked_ref))

    db.session.add(edition)
    db.session.commit()

    if build is not None:
        request_edition_rebuild(edition=edition, build=build)

    request_dashboard_build(product)

    return edition


SEMVER_PATTERN = re.compile(
    r"^v?(?P<major>[\d]+)(\.(?P<minor>[\d]+)(\.(?P<patch>[\d]+))?)?$"
)


def determine_edition_kind(git_ref: str) -> str:
    """Determine the kind of edition based on the git ref."""
    match = SEMVER_PATTERN.match(git_ref)
    if match is None:
        return "draft"

    if match.group("patch") is not None and match.group("minor") is not None:
        return "release"

    if match.group("minor") is not None and match.group("patch") is None:
        return "minor"

    return "major"
