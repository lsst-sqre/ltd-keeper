"""Handers for v2 build endpoints."""

from __future__ import annotations

from typing import Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.logutils import log_route
from keeper.models import Build, Organization, Product, db
from keeper.services.createbuild import (
    create_build,
    create_presigned_post_urls,
)
from keeper.services.updatebuild import update_build
from keeper.taskrunner import launch_tasks
from keeper.v2api import v2api

from ._models import (
    BuildPatchRequest,
    BuildPostRequest,
    BuildResponse,
    BuildsResponse,
)
from ._urls import url_for_build

__all__ = ["get_builds", "get_build", "post_build", "patch_build"]


@v2api.route("/orgs/<org>/projects/<project>/builds", methods=["GET"])
@accept_fallback
@log_route()
def get_builds(org: str, project: str) -> str:
    builds = (
        Build.query.join(Product, Product.id == Build.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .all()
    )
    response = BuildsResponse.from_builds(builds)
    return response.json()


@v2api.route("/orgs/<org>/projects/<project>/builds/<id>", methods=["GET"])
@accept_fallback
@log_route()
def get_build(org: str, project: str, id: str) -> str:
    build = (
        Build.query.join(Product, Product.id == Build.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .filter(Build.slug == id)
        .first_or_404()
    )
    response = BuildResponse.from_build(build)
    return response.json()


@v2api.route("/orgs/<org>/projects/<project>/builds", methods=["POST"])
@accept_fallback
@log_route()
def post_build(org: str, project: str) -> Tuple[str, int, Dict[str, str]]:
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .first_or_404()
    )

    request_data = BuildPostRequest.parse_obj(request.json)

    try:
        build, edition = create_build(
            product=product,
            git_ref=request_data.git_ref,
            github_requester=None,
            slug=request_data.slug,
        )
    except Exception:
        db.session.rollback()
        raise

    presigned_prefix_urls, presigned_dir_urls = create_presigned_post_urls(
        build=build, directories=request_data.directories
    )

    build_response = BuildResponse.from_build(
        build,
        post_prefix_urls=presigned_prefix_urls,
        post_dir_urls=presigned_dir_urls,
    )
    build_url = url_for_build(build)

    return build_response.json(), 201, {"Location": build_url}


@v2api.route("/orgs/<org>/projects/<project>/builds/<id>", methods=["PATCH"])
@accept_fallback
@log_route()
def patch_build(
    org: str, project: str, id: str
) -> Tuple[str, int, Dict[str, str]]:
    build = (
        Build.query.join(Product, Product.id == Build.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == org)
        .filter(Product.slug == project)
        .filter(Build.slug == id)
        .first_or_404()
    )

    request_data = BuildPatchRequest.parse_obj(request.json)

    try:
        build = update_build(build=build, uploaded=request_data.uploaded)
    except Exception:
        db.session.rollback()

    # Run the task queue
    task = launch_tasks()

    build_url = url_for_build(build)
    response = BuildResponse.from_build(build, task=task)
    return (
        response.json(),
        202,
        {"Location": build_url},
    )
