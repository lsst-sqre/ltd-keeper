"""Handlers for the v2 edition endpoints."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.auth import token_auth
from keeper.logutils import log_route
from keeper.models import Build, Edition, Organization, Product, db
from keeper.services.createedition import create_edition
from keeper.services.updateedition import update_edition
from keeper.taskrunner import launch_tasks
from keeper.v2api import v2api

from ._models import (
    EditionPatchRequest,
    EditionPostRequest,
    EditionResponse,
    EditionsResponse,
)
from ._urls import build_from_url, url_for_edition

__all__ = ["get_editions", "get_edition", "post_edition", "patch_edition"]


@v2api.route("/orgs/<org>/projects/<project>/editions", methods=["GET"])
@accept_fallback
@log_route()
@token_auth.login_required
def get_editions(org: str, project: str) -> str:
    editions = (
        Edition.query.join(Product, Product.id == Edition.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .all()
    )
    response = EditionsResponse.from_editions(editions)
    return response.json()


@v2api.route("/orgs/<org>/projects/<project>/editions/<id>", methods=["GET"])
@accept_fallback
@log_route()
@token_auth.login_required
def get_edition(org: str, project: str, id: str) -> str:
    edition = (
        Edition.query.join(Product, Product.id == Edition.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .filter(Edition.slug == id)
        .first_or_404()
    )
    response = EditionResponse.from_edition(edition)
    return response.json()


@v2api.route("/orgs/<org>/projects/<project>/editions", methods=["POST"])
@accept_fallback
@log_route()
@token_auth.login_required
def post_edition(org: str, project: str) -> Tuple[str, int, Dict[str, str]]:
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .first_or_404()
    )

    request_data = EditionPostRequest.parse_obj(request.json)

    if request_data.build_url:
        build: Optional[Build] = build_from_url(request_data.build_url)
    else:
        build = None

    try:
        edition = create_edition(
            product=product,
            title=request_data.title,
            tracking_mode=request_data.mode,
            slug=request_data.slug,
            autoincrement_slug=request_data.autoincrement,
            tracked_ref=request_data.tracked_ref,
            build=build,
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()
    response = EditionResponse.from_edition(edition, task=task)
    edition_url = url_for_edition(edition)
    return response.json(), 202, {"Location": edition_url}


@v2api.route("/orgs/<org>/projects/<project>/editions/<id>", methods=["PATCH"])
@accept_fallback
@log_route()
@token_auth.login_required
def patch_edition(
    org: str, project: str, id: str
) -> Tuple[str, int, Dict[str, str]]:
    edition = (
        Edition.query.join(Product, Product.id == Edition.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .filter(Edition.slug == id)
        .all()
    )
    request_data = EditionPatchRequest.parse_obj(request.json)

    if request_data.build_url:
        build: Optional[Build] = build_from_url(request_data.build_url)
    else:
        build = None

    try:
        edition = update_edition(
            edition=edition,
            build=build,
            title=request_data.title,
            slug=request_data.slug,
            tracking_mode=request_data.mode,
            tracked_ref=request_data.tracked_ref,
            pending_rebuild=request_data.pending_rebuild,
        )
    except Exception:
        db.session.rollback()
        raise

    # Run the task queue
    task = launch_tasks()

    response = EditionResponse.from_edition(edition, task=task)
    edition_url = url_for_edition(edition)
    return response.json(), 202, {"Location": edition_url}
