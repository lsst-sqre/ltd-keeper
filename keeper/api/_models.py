"""Pydantic Models for the v1 API endpoints."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, HttpUrl, validator

from keeper.editiontracking import EditionTrackingModes
from keeper.exceptions import ValidationError
from keeper.utils import (
    format_utc_datetime,
    validate_path_slug,
    validate_product_slug,
)

from ._urls import (
    url_for_build,
    url_for_edition,
    url_for_product,
    url_for_task,
)

if TYPE_CHECKING:
    import celery

    from keeper.models import Build, Edition, Product


class PresignedPostUrl(BaseModel):
    """An S3 presigned post URL and associated metadata."""

    url: HttpUrl
    """The presigned post URL."""

    fields: Dict[str, Any]
    """Additional metadata."""


class QueuedResponse(BaseModel):
    """Response that contains only a URL for the background task's status."""

    queue_url: Optional[HttpUrl]
    """The URL for the queued task resource."""

    @classmethod
    def from_task(cls, task: Optional[celery.Task]) -> QueuedResponse:
        return cls(queue_url=url_for_task(task) if task is not None else None)


class BuildResponse(BaseModel):
    """The build resource."""

    self_url: HttpUrl
    """The URL of the build resource."""

    product_url: HttpUrl
    """The URL or the build's associated product resource."""

    slug: str
    """The build's URL-safe slug."""

    date_created: datetime.datetime
    """The date when the build was created (UTC)."""

    date_ended: Optional[datetime.datetime]
    """The date when the build was created (UTC)."""

    uploaded: bool
    """True if the built documentation has been uploaded to the S3 bucket.
    Use PATCH `/builds/(int:id)` to set this to `True`
    """

    bucket_name: str
    """Name of the S3 bucket hosting the built documentation."""

    bucket_root_dir: str
    """Directory (path prefix) in the S3 bucket where this documentation
    build is located.
    """

    git_refs: Optional[List[str]]
    """Git ref array that describes the version of the documentation being
    built. Typically this array will be a single string, e.g. ``['main']`` but
    may be a list of several refs for multi-package builds with ltd-conveyor.
    """

    github_requester: Optional[str]
    """The GitHub username of the person who triggered the build."""

    published_url: HttpUrl
    """The URL where the build is published on the web."""

    surrogate_key: str
    """The surrogate key attached to the headers of all files on S3 belonging
    to this build. This allows LTD Keeper to notify Fastly when an Edition is
    being re-pointed to a new build. The client is responsible for uploading
    files with this value as the ``x-amz-meta-surrogate-key`` value.
    """

    queue_url: Optional[HttpUrl] = None
    """The URL of any queued task resource."""

    post_prefix_urls: Optional[Dict[str, PresignedPostUrl]] = None
    """AWS S3 presigned-post URLs for prefixes."""

    post_dir_urls: Optional[Dict[str, PresignedPostUrl]] = None
    """AWS S3 presigned-post URLs for directories."""

    @classmethod
    def from_build(
        cls,
        build: Build,
        task: celery.Task = None,
        post_prefix_urls: Optional[Mapping[str, Any]] = None,
        post_dir_urls: Optional[Mapping[str, Any]] = None,
    ) -> BuildResponse:
        """Create a BuildResponse from the Build ORM model instance."""
        obj: Dict[str, Any] = {
            "self_url": url_for_build(build),
            "product_url": url_for_product(build.product),
            "slug": build.slug,
            "date_created": build.date_created,
            "date_ended": build.date_ended,
            "uploaded": build.uploaded,
            "bucket_name": build.bucket_name,
            "bucket_root_dir": build.bucket_root_dirname,
            "git_refs": build.git_refs,
            "github_requester": build.github_requester,
            "published_url": build.published_url,
            "surrogate_key": build.surrogate_key,
            "queue_url": url_for_task(task) if task is not None else None,
            "post_prefix_urls": post_prefix_urls,
            "post_dir_urls": post_dir_urls,
        }
        return cls.parse_obj(obj)

    class Config:
        json_encoders = {
            datetime.datetime: format_utc_datetime,
        }


class BuildUrlListingResponse(BaseModel):
    """The listing of build resource URLs."""

    builds: List[HttpUrl]


class BuildPostRequest(BaseModel):
    """Model for a POST /products/<slug>/builds endpoint."""

    git_refs: List[str]

    github_requester: Optional[str] = None

    slug: Optional[str] = None

    @validator("slug")
    def check_slug(cls, v: str) -> str:
        try:
            validate_path_slug(v)
        except ValidationError:
            raise ValueError(f"Slug {v!r} is incorrectly formatted.")
        return v


class BuildPostRequestWithDirs(BuildPostRequest):
    """Model for a POST /products/<slug>/builds endpoint with
    application/vnd.ltdkeeper.v2+json application type.
    """

    directories: List[str] = Field(default_factory=lambda: ["/"])

    @validator("directories")
    def check_directories(cls, v: List[str]) -> List[str]:
        new_list: List[str] = []
        for d in v:
            d = d.strip()
            if not d.endswith("/"):
                d = f"{d}/"
            new_list.append(d)
        return new_list


class BuildPatchRequest(BaseModel):
    """Model for a PATCH /builds/:id endpoint."""

    uploaded: Optional[bool] = None
    """True if the built documentation has been uploaded to the S3 bucket.
    """


class EditionResponse(BaseModel):
    """The edition resource."""

    self_url: HttpUrl
    """The URL of the edition resource."""

    product_url: HttpUrl
    """The URL or the edition's associated product resource."""

    build_url: Optional[HttpUrl]
    """The URL or the build's associated product resource. This is null if
    the edition doesn't have a build yet.
    """

    published_url: HttpUrl
    """The web URL for this edition."""

    slug: str
    """The edition's URL-safe slug."""

    title: str
    """The edition's title."""

    date_created: datetime.datetime
    """The date when the build was created (UTC)."""

    date_rebuilt: datetime.datetime
    """The date when associated build was last updated (UTC)."""

    date_ended: Optional[datetime.datetime]
    """The date when the build was created (UTC). Is null if the edition
    has not been deleted.
    """

    surrogate_key: str
    """The surrogate key attached to the headers of all files on S3 belonging
    to this edition. This allows LTD Keeper to notify Fastly when an Edition is
    being re-pointed to a new build. The client is responsible for uploading
    files with this value as the ``x-amz-meta-surrogate-key`` value.
    """

    pending_rebuild: bool
    """Flag indicating if the edition is currently being rebuilt with a new
    build.
    """

    tracked_refs: Optional[List[str]]
    """Git ref(s) that describe the version of the Product that this this
    Edition is intended to point to when using the ``git_refs`` tracking mode.
    """

    mode: str
    """The edition tracking mode."""

    queue_url: Optional[HttpUrl] = None
    """The URL of any queued task resource."""

    @classmethod
    def from_edition(
        cls,
        edition: Edition,
        task: celery.Task = None,
    ) -> EditionResponse:
        """Create an EditionResponse from the Edition ORM model instance."""
        if edition.mode_name == "git_refs":
            tracked_refs = edition.tracked_refs
        elif edition.mode_name == "git_ref":
            tracked_refs = [edition.tracked_ref]
        else:
            tracked_refs = None

        obj: Dict[str, Any] = {
            "self_url": url_for_edition(edition),
            "product_url": url_for_product(edition.product),
            "build_url": (
                url_for_build(edition.build)
                if edition.build is not None
                else None
            ),
            "published_url": edition.published_url,
            "slug": edition.slug,
            "title": edition.title,
            "date_created": edition.date_created,
            "date_rebuilt": edition.date_rebuilt,
            "date_ended": edition.date_ended,
            "mode": edition.mode_name,
            "tracked_refs": tracked_refs,
            "pending_rebuild": edition.pending_rebuild,
            "surrogate_key": edition.surrogate_key,
            "queue_url": url_for_task(task) if task is not None else None,
        }
        return cls.parse_obj(obj)

    class Config:
        json_encoders = {
            datetime.datetime: format_utc_datetime,
        }


class EditionUrlListingResponse(BaseModel):
    """The listing of edition resource URLs."""

    editions: List[HttpUrl]


class EditionPostRequest(BaseModel):
    """The request body for the POST /products/<product>/editions endpoint."""

    title: Optional[str] = None
    """The human-readable title of the edition. Can be left as None if
    autoincrement is true.
    """

    slug: Optional[str] = None
    """The edition's path-safe slug."""

    autoincrement: Optional[bool] = False
    """Assigned a slug as an auto-incremented integer, rather than use
    ``slug``.
    """

    build_url: Optional[HttpUrl] = None
    """URL of the build to initially publish with the edition, if available.
    """

    mode: str = "git_refs"
    """Tracking mode."""

    tracked_refs: Optional[List[str]] = None
    """Git refs being tracked if mode is ``git_refs``."""

    @validator("slug")
    def check_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        else:
            try:
                validate_path_slug(v)
            except ValidationError:
                raise ValueError(f"Slug {v!r} is incorrectly formatted.")
            return v

    @validator("mode")
    def check_mode(cls, v: str) -> str:
        modes = EditionTrackingModes()
        if v not in modes:
            raise ValueError(f"Tracking mode {v!r} is not known.")
        return v

    @validator("autoincrement")
    def check_autoincrement(cls, v: bool, values: Mapping[str, Any]) -> bool:
        """Verify that autoincrement is False if a slug is given, and that
        a title is given if autoincrement is False.
        """
        slug_is_none = values.get("slug") is None
        if slug_is_none and v is False:
            raise ValueError("A slug must be set if autoincrement is false.")
        elif not slug_is_none and v is True:
            raise ValueError(
                "A slug cannot be set in conjunction with "
                "autoincrement = true"
            )

        if values.get("title") is None and v is False:
            raise ValueError("A title is required if autoincrement is false")
        return v

    @validator("tracked_refs")
    def check_tracked_refs(
        cls, v: Optional[List[str]], values: Mapping[str, Any]
    ) -> Optional[List[str]]:
        if values.get("mode") == "git_refs" and v is None:
            raise ValueError('tracked_refs must be set is mode is "git_refs"')
        return v


class EditionPatchRequest(BaseModel):
    """The model for a PATCH /editions/:id request."""

    slug: Optional[str] = None
    """The edition's URL-safe slug."""

    title: Optional[str] = None
    """The edition's title."""

    pending_rebuild: Optional[bool] = None
    """Flag indicating if the edition is currently being rebuilt with a new
    build.
    """

    tracked_refs: Optional[List[str]] = None
    """Git ref(s) that describe the version of the Product that this this
    Edition is intended to point to when using the ``git_refs`` tracking mode.
    """

    mode: Optional[str] = None
    """The edition tracking mode."""

    build_url: Optional[HttpUrl] = None
    """URL of the build to initially publish with the edition, if available.
    """

    @validator("slug")
    def check_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        else:
            try:
                validate_path_slug(v)
            except ValidationError:
                raise ValueError(f"Slug {v!r} is incorrectly formatted.")
            return v

    @validator("mode")
    def check_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        modes = EditionTrackingModes()
        if v not in modes:
            raise ValueError(f"Tracking mode {v!r} is not known.")
        return v


class ProductResponse(BaseModel):
    """The product resource."""

    self_url: HttpUrl
    """The URL of the product resource."""

    slug: str
    """URL/path-safe identifier for this product (unique)."""

    doc_repo: HttpUrl
    """URL of the associated source repository (GitHub homepage)."""

    title: str
    """Title of this product."""

    root_domain: str
    """Root domain name serving docs (e.g., lsst.io)."""

    root_fastly_domain: str
    """Fastly CDN domain name (without doc's domain prepended)."""

    domain: str
    """Domain where docs for this product are served from.

    (E.g. ``product.lsst.io`` if ``product`` is the slug and ``lsst.io``
    is the ``root_domain``.)
    """

    fastly_domain: str
    """Domain where Fastly serves content from for this product."""

    bucket_name: Optional[str]
    """Name of the S3 bucket hosting builds."""

    published_url: HttpUrl
    """URL where this product's main edition is published on the web."""

    surrogate_key: str
    """surrogate_key for Fastly quick purges of dashboards.

    Editions and Builds have independent surrogate keys.
    """

    @classmethod
    def from_product(
        cls,
        product: Product,
        task: celery.Task = None,
    ) -> ProductResponse:
        """Create a ProductResponse from the Product ORM model instance."""
        obj: Dict[str, Any] = {
            "self_url": url_for_product(product),
            "slug": product.slug,
            "doc_repo": product.doc_repo,
            "title": product.title,
            "root_domain": product.root_domain,
            "root_fastly_domain": product.root_fastly_domain,
            "domain": product.domain,
            "fastly_domain": product.fastly_domain,
            "bucket_name": product.bucket_name,
            "published_url": product.published_url,
            "surrogate_key": product.surrogate_key,
            "queue_url": url_for_task(task) if task is not None else None,
        }
        return cls.parse_obj(obj)


class ProductUrlListingResponse(BaseModel):
    """The listing of product resource URLs."""

    products: List[HttpUrl]
    """Listing of product resource URLs."""


class ProductPostRequest(BaseModel):
    """Model for a POST /products/ request body."""

    slug: str
    """URL/path-safe identifier for this product (unique)."""

    doc_repo: HttpUrl
    """URL of the associated source repository (GitHub homepage)."""

    title: str
    """Title of this product."""

    root_domain: str
    """Root domain name serving docs (e.g., lsst.io)."""

    root_fastly_domain: str
    """Fastly CDN domain name (without doc's domain prepended)."""

    bucket_name: Optional[str]
    """Name of the S3 bucket hosting builds."""

    main_mode: Optional[str]
    """Tracking mode of the main edition."""

    @validator("slug")
    def check_slug(cls, v: str) -> str:
        try:
            validate_product_slug(v)
        except ValidationError:
            raise ValueError(f"Slug {v!r} is incorrectly formatted.")
        return v

    @validator("main_mode")
    def check_main_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        modes = EditionTrackingModes()
        if v in modes:
            return v
        else:
            raise ValueError(f"Tracking mode {v!r} is not known.")


class ProductPatchRequest(BaseModel):
    """Model for a PATCH /products/<slug> request body."""

    doc_repo: Optional[HttpUrl] = None
    """New URL of the associated source repository (GitHub homepage)."""

    title: Optional[str] = None
    """New title of this product."""

    class Config:
        # We want to invalidate requests that attempt to patch and fields
        # that aren't mutable.
        extra = "forbid"
