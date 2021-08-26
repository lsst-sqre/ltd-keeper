"""Internal URLs for v2 API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

if TYPE_CHECKING:
    from keeper.models import Organization

__all__ = ["url_for_organization"]


def url_for_organization(org: Organization) -> str:
    """Get the v2 URL for an organization resource."""
    return url_for("v2api.get_organization", slug=org.slug, _external=True)
