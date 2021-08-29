"""Internal URLs for v2 API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

from keeper.exceptions import ValidationError
from keeper.models import Organization, Product
from keeper.utils import split_url

if TYPE_CHECKING:
    import celery

    from keeper.models import Build

__all__ = [
    "url_for_organization",
    "url_for_organization_projects",
    "url_for_project",
    "url_for_build",
    "url_for_project_builds",
    "url_for_task",
    "product_from_url",
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


def url_for_build(build: Build) -> str:
    """Get the v2 URL for a build resource."""
    return url_for(
        "v2api.get_build",
        org=build.product.organization.slug,
        project=build.product.slug,
        id=build.slug,
        _external=True,
    )


def url_for_project_builds(product: Product) -> str:
    """Get the v2 URL for a project's builds."""
    return url_for(
        "v2api.get_builds",
        org=product.organization.slug,
        project=product.slug,
        _external=True,
    )


def url_for_task(task: celery.Task) -> str:
    """Get the v2 URL for a task resource."""
    return url_for(
        "v2api.get_task",
        id=task.id,
        _external=True,
    )


def product_from_url(product_url: str) -> Product:
    product_endpoint, product_args = split_url(product_url)
    if product_endpoint != "v2api.get_project":
        raise ValidationError("Invalid product_url: {}".format(product_url))

    try:
        project_slug = product_args["slug"]
        org_slug = product_args["org"]
    except KeyError:
        raise ValidationError("Invalid product_url: {}".format(product_url))

    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org_slug)
        .filter(Product.slug == project_slug)
        .first_or_404()
    )
    return product
