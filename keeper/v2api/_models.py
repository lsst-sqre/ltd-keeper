"""Pydantic models for the v2 API endpoints."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, HttpUrl, SecretStr, validator

from keeper.editiontracking import EditionTrackingModes
from keeper.exceptions import ValidationError
from keeper.models import OrganizationLayoutMode
from keeper.utils import validate_path_slug, validate_product_slug

from ._urls import (
    url_for_organization,
    url_for_organization_projects,
    url_for_project,
)

if TYPE_CHECKING:
    import celery

    from keeper.models import Organization, Product

__all__ = [
    "OrganizationResponse",
    "OrganizationsResponse",
    "OrganizationPostRequest",
    "ProjectResponse",
    "ProjectsResponse",
    "ProjectPostRequest",
    "ProjectPatchRequest",
]


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

    projects_url: HttpUrl
    """The URL for the organization's projects."""

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
            projects_url=url_for_organization_projects(org),
        )


class LayoutEnum(str, Enum):

    subdomain = "subdomain"

    path = "path"

    @property
    def layout_model_enum(self) -> OrganizationLayoutMode:
        return OrganizationLayoutMode[self.name]


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


class OrganizationPostRequest(BaseModel):
    """A model for creating an organization with the POST method."""

    slug: str
    """The name of the organization in the API."""

    title: str
    """The presentational name of the organization."""

    layout: LayoutEnum
    """The layout mode."""

    domain: str
    """The domain where documentation is served from (e.g. lsst.io)."""

    path_prefix: str
    """The path prefix where documentation is served from (e.g. "/"
    if documentation is served from the root of a domain.
    """

    bucket_name: str
    """Name of the S3 bucket hosting builds."""

    fastly_support: bool
    """Toggle to enable Fastly CDN support."""

    fastly_domain: Optional[str] = None
    """Fastly CDN domain name (without doc's domain prepended)."""

    fastly_service_id: Optional[str] = None
    """The Fastly service ID."""

    fastly_api_key: Optional[SecretStr] = None
    """The Fastly API key."""

    @validator("slug")
    def check_slug(cls, v: str) -> str:
        try:
            validate_path_slug(v)
        except ValidationError:
            raise ValueError(f"Slug {v!r} is incorrectly formatted.")
        return v

    @validator("fastly_domain")
    def check_fastly_domain(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values["fastly_support"]:
            if v is None:
                raise ValueError(
                    "Set fastly_domain since fastly_support is enabled."
                )
        return v

    @validator("fastly_service_id")
    def check_fastly_service_id(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values["fastly_support"]:
            if v is None:
                raise ValueError(
                    "Set fastly_service_id since fastly_support is enabled."
                )
        return v

    @validator("fastly_api_key")
    def check_fastly_api_key(
        cls, v: Optional[SecretStr], values: Dict[str, Any]
    ) -> Optional[SecretStr]:
        if values["fastly_support"]:
            if v is None:
                raise ValueError(
                    "Set fastly_api_key since fastly_support is enabled."
                )
        return v


class ProjectResponse(BaseModel):
    """The project resource."""

    self_url: HttpUrl
    """The URL of the project resource."""

    organization_url: HttpUrl
    """The URL of the organization resource."""

    slug: str
    """URL/path-safe identifier for this project (unique within an
    organization).
    """

    source_repo_url: HttpUrl
    """URL of the associated source repository (GitHub homepage)."""

    title: str
    """Title of this project."""

    published_url: HttpUrl
    """URL where this project's default edition is published on the web."""

    surrogate_key: str
    """surrogate_key for Fastly quick purges of dashboards.

    Editions and Builds have independent surrogate keys.
    """

    @classmethod
    def from_product(
        cls,
        product: Product,
        task: celery.Task = None,
    ) -> ProjectResponse:
        """Create a ProjectResponse from the Product ORM model instance."""
        obj: Dict[str, Any] = {
            "self_url": url_for_project(product),
            "organization_url": url_for_organization(product.organization),
            "slug": product.slug,
            "title": product.title,
            "source_repo_url": product.doc_repo,
            "published_url": product.published_url,
            "surrogate_key": product.surrogate_key,
            # "queue_url": url_for_task(task) if task is not None else None,
        }
        return cls.parse_obj(obj)


class ProjectsResponse(BaseModel):
    """A model for a collection of project responses."""

    __root__: List[ProjectResponse]

    @classmethod
    def from_products(cls, products: List[Product]) -> ProjectsResponse:
        project_responses = [
            ProjectResponse.from_product(product) for product in products
        ]
        return cls(__root__=project_responses)


class ProjectPostRequest(BaseModel):
    """A model for specifying a new project in a POST method."""

    slug: str
    """URL/path-safe identifier for this project (unique)."""

    source_repo_url: HttpUrl
    """URL of the associated source repository (GitHub homepage)."""

    title: str
    """Title of this project."""

    default_edition_mode: Optional[str]
    """Tracking mode of the default edition."""

    @validator("slug")
    def check_slug(cls, v: str) -> str:
        try:
            validate_product_slug(v)
        except ValidationError:
            raise ValueError(f"Slug {v!r} is incorrectly formatted.")
        return v

    @validator("default_edition_mode")
    def check_default_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        modes = EditionTrackingModes()
        if v in modes:
            return v
        else:
            raise ValueError(f"Tracking mode {v!r} is not known.")


class ProjectPatchRequest(BaseModel):
    """A model for updating a project in a PATCH method."""

    source_repo_url: Optional[HttpUrl]
    """URL of the associated source repository (GitHub homepage)."""

    title: Optional[str]
    """Title of this project."""

    class Config:
        # We want to invalidate requests that attempt to patch and fields
        # that aren't mutable.
        extra = "forbid"
