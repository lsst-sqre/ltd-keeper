"""Handlers for organization-related APIs."""

from __future__ import annotations

from flask_accept import accept_fallback

from keeper.logutils import log_route
from keeper.models import Organization
from keeper.v2api import v2api

from ._models import OrganizationResponse, OrganizationsResponse

__all__ = ["get_organization", "get_organization"]


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
