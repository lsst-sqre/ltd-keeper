"""Handlers for project-related APIs."""

from __future__ import annotations

from typing import Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.logutils import log_route
from keeper.models import Organization, Product, db
from keeper.services.createproduct import create_product
from keeper.services.updateproduct import update_product
from keeper.taskrunner import launch_tasks
from keeper.v2api import v2api

from ._models import (
    ProjectPatchRequest,
    ProjectPostRequest,
    ProjectResponse,
    ProjectsResponse,
)
from ._urls import url_for_project

__all__ = ["get_projects", "get_project", "create_project", "update_project"]


@v2api.route("/orgs/<org>/projects", methods=["GET"])
@accept_fallback
@log_route()
def get_projects(org: str) -> str:
    products = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org)
        .all()
    )
    response = ProjectsResponse.from_products(products)
    return response.json()


@v2api.route("/orgs/<org>/projects/<slug>", methods=["GET"])
@accept_fallback
@log_route()
def get_project(org: str, slug: str) -> str:
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org)
        .filter(Product.slug == slug)
        .first_or_404()
    )
    response = ProjectResponse.from_product(product)
    return response.json()


@v2api.route("/orgs/<org>/projects", methods=["POST"])
@accept_fallback
@log_route()
def create_project(org: str) -> Tuple[str, int, Dict[str, str]]:
    request_data = ProjectPostRequest.parse_obj(request.json)

    organization = Organization.query.filter(
        Organization.slug == org
    ).first_or_404()

    try:
        product, default_edition = create_product(
            org=organization,
            slug=request_data.slug,
            doc_repo=request_data.source_repo_url,
            title=request_data.title,
            default_edition_mode=(
                request_data.default_edition_mode
                if request_data.default_edition_mode is not None
                else None
            ),
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()

    response = ProjectResponse.from_product(product, task=task)
    project_url = url_for_project(product)
    return response.json(), 201, {"Location": project_url}


@v2api.route("/orgs/<org>/projects/<slug>", methods=["PATCH"])
@accept_fallback
@log_route()
def update_project(org: str, slug: str) -> Tuple[str, int, Dict[str, str]]:
    request_data = ProjectPatchRequest.parse_obj(request.json)

    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org)
        .filter(Product.slug == slug)
        .first_or_404()
    )

    try:
        product = update_product(
            product=product,
            new_doc_repo=request_data.source_repo_url,
            new_title=request_data.title,
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()
    response = ProjectResponse.from_product(product, task=task)
    project_url = url_for_project(product)
    return response.json(), 200, {"Location": project_url}
