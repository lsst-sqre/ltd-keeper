"""Functions for creating URLs for ORM resources as their GET endpoints
in the v1 API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

from keeper.exceptions import ValidationError
from keeper.models import Build, Edition, Product
from keeper.utils import split_url

if TYPE_CHECKING:
    import celery


def url_for_product(product: Product) -> str:
    return url_for("api.get_product", slug=product.slug, _external=True)


def url_for_edition(edition: Edition) -> str:
    return url_for("api.get_edition", id=edition.id, _external=True)


def url_for_build(build: Build) -> str:
    return url_for("api.get_build", id=build.id, _external=True)


def url_for_task(task: celery.Task) -> str:
    return url_for("api.get_task_status", id=task.id, _external=True)


def product_from_url(product_url: str) -> Product:
    product_endpoint, product_args = split_url(product_url)
    if product_endpoint != "api.get_product" or "slug" not in product_args:
        raise ValidationError("Invalid product_url: {}".format(product_url))
    slug = product_args["slug"]
    product = Product.query.filter_by(slug=slug).first_or_404()
    return product


def build_from_url(build_url: str) -> Build:
    build_endpoint, build_args = split_url(build_url)
    if build_endpoint != "api.get_build" or "id" not in build_args:
        raise ValidationError("Invalid build_url: {}".format(build_url))
    build = Build.query.get(build_args["id"])
    if build is None:
        raise ValidationError("Invalid build_url: " + build_url)
    return build


def edition_from_url(edition_url: str) -> Edition:
    edition_endpoint, endpoint_args = split_url(edition_url)
    if edition_endpoint != "api.get_edition" or "id" not in endpoint_args:
        raise ValidationError("Invalid edition_url: {}".format(edition_url))
    edition = Edition.query.get(endpoint_args["id"])
    if edition is None:
        raise ValidationError("Invalid build_url: " + edition_url)
    return edition
