"""Internal URLs for v2 API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

from keeper.exceptions import ValidationError
from keeper.models import Build, Edition, Organization, Product
from keeper.utils import split_url

if TYPE_CHECKING:
    import celery

__all__ = [
    "url_for_organization",
    "url_for_organization_projects",
    "url_for_project",
    "url_for_build",
    "url_for_project_builds",
    "url_for_edition",
    "url_for_project_editions",
    "url_for_task",
    "product_from_url",
    "build_from_url",
    "edition_from_url",
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


def url_for_edition(edition: Edition) -> str:
    """Get the v2 URL for an edition resource."""
    return url_for(
        "v2api.get_edition",
        org=edition.product.organization.slug,
        project=edition.product.slug,
        id=edition.slug,
        _external=True,
    )


def url_for_project_editions(product: Product) -> str:
    """Get the v2 URL for a project's builds."""
    return url_for(
        "v2api.get_editions",
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


def build_from_url(build_url: str) -> Build:
    endpoint, args = split_url(build_url)
    if endpoint != "v2api.get_build":
        raise ValidationError("Invalid build_url: {}".format(build_url))

    try:
        project_slug = args["project"]
        org_slug = args["org"]
        build_slug = args["id"]
    except KeyError:
        raise ValidationError("Invalid build_url: {}".format(build_url))

    build = (
        Build.query.join(Product, Product.id == Build.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org_slug)
        .filter(Product.slug == project_slug)
        .filter(Build.slug == build_slug)
        .first_or_404()
    )
    return build


def edition_from_url(edition_url: str) -> Edition:
    endpoint, args = split_url(edition_url)

    if endpoint != "v2api.get_edition":
        raise ValidationError("Invalid edition_url: {}".format(edition_url))

    try:
        project_slug = args["project"]
        org_slug = args["org"]
        edition_slug = args["id"]
    except KeyError:
        raise ValidationError("Invalid edition_url: {}".format(edition_url))

    edition = (
        Edition.query.join(Product, Product.id == Edition.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org_slug)
        .filter(Product.slug == project_slug)
        .filter(Edition.slug == edition_slug)
        .first_or_404()
    )
    return edition
