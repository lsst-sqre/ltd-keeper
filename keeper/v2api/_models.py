"""Pydantic models for the v2 API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, HttpUrl

from ._urls import url_for_organization

if TYPE_CHECKING:
    from keeper.models import Organization

__all__ = ["OrganizationResponse"]


class OrganizationResponse(BaseModel):
    """A model for the organization resource."""

    slug: str
    """Identifier for this organization in the API."""

    title: str
    """Presentational name of this organization."""

    layout: str
    """The layout mode."""

    domain: str
    """Domain name serving the documentation."""

    path_prefix: str
    """The path prefix where documentation is served."""

    fastly_support: bool
    """Flag indicating is Fastly CDN support is enabled."""

    fastly_domain: Optional[HttpUrl]
    """The Fastly CDN domain name."""

    fastly_service_id: Optional[str]
    """The Fastly service ID."""

    s3_bucket: Optional[str]
    """Name of the S3 bucket hosting builds."""

    self_url: HttpUrl
    """The URL of the organization response."""

    @classmethod
    def from_organization(cls, org: Organization) -> OrganizationResponse:
        return cls(
            slug=org.slug,
            title=org.title,
            layout=org.layout.name,
            domain=org.root_domain,
            path_prefix=org.root_path_prefix,
            fastly_support=org.fastly_support,
            fastly_service_id=(
                org.fastly_service_id if org.fastly_support else None
            ),
            s3_bucket=org.bucket_name,
            self_url=url_for_organization(org),
        )


class OrganizationsResponse(BaseModel):
    """A model for a collection of organization responses."""

    __root__: List[OrganizationResponse]

    @classmethod
    def from_organizations(
        cls, orgs: List[Organization]
    ) -> OrganizationsResponse:
        org_responses = [
            OrganizationResponse.from_organization(org) for org in orgs
        ]
        return cls(__root__=org_responses)
