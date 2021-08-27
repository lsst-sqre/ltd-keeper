"""Handlers for organization-related APIs."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.logutils import log_route
from keeper.models import Organization, db
from keeper.services import createorg
from keeper.v2api import v2api

from ._models import (
    OrganizationPostRequest,
    OrganizationResponse,
    OrganizationsResponse,
)
from ._urls import url_for_organization

__all__ = ["get_organization", "get_organizations", "create_organization"]


@v2api.route("/orgs", methods=["GET"])
@accept_fallback
@log_route()
def get_organizations() -> str:
    """List organizations."""
    response = OrganizationsResponse.from_organizations(
        [org for org in Organization.query.all()]
    )
    return response.json()


@v2api.route("/orgs/<slug>", methods=["GET"])
@accept_fallback
@log_route()
def get_organization(slug: str) -> str:
    """Get a single organization's resource."""
    org = Organization.query.filter_by(slug=slug).first_or_404()
    response = OrganizationResponse.from_organization(org)
    return response.json()


@v2api.route("/orgs", methods=["POST"])
@accept_fallback
@log_route()
def create_organization() -> Tuple[str, int, Dict[str, Any]]:
    request_data = OrganizationPostRequest.parse_obj(request.json)

    try:
        org = createorg.create_organization(
            slug=request_data.slug,
            title=request_data.title,
            layout=request_data.layout.layout_model_enum,
            domain=request_data.domain,
            path_prefix=request_data.path_prefix,
            bucket_name=request_data.bucket_name,
            fastly_support=request_data.fastly_support,
            fastly_domain=request_data.fastly_domain,
            fastly_service_id=request_data.fastly_service_id,
            fastly_api_key=request_data.fastly_api_key,
        )
    except Exception:
        db.session.rollback()
        raise

    response = OrganizationResponse.from_organization(org)
    org_url = url_for_organization(org)
    return response.json(), 201, {"Location": org_url}
