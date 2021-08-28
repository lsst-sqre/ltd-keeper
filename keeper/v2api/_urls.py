"""Internal URLs for v2 API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

if TYPE_CHECKING:
    import celery

    from keeper.models import Organization, Product

__all__ = [
    "url_for_organization",
    "url_for_organization_projects",
    "url_for_project",
    "url_for_task",
]


def url_for_organization(org: Organization) -> str:
    """Get the v2 URL for an organization resource."""
    return url_for("v2api.get_organization", slug=org.slug, _external=True)


def url_for_organization_projects(org: Organization) -> str:
    """Get the v2 URL for an organization's projects."""
    return url_for("v2api.get_projects", org=org.slug, _external=True)


def url_for_project(product: Product) -> str:
    """Get the v2 URL for an organization resource."""
    return url_for(
        "v2api.get_project",
        org=product.organization.slug,
        slug=product.slug,
        _external=True,
    )


def url_for_task(task: celery.Task) -> str:
    """Get the v2 URL for a task resource."""
    return url_for(
        "v2api.get_task",
        id=task.id,
        _external=True,
    )
