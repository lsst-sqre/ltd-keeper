"""Pydantic Models for the v1 API endpoints."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, HttpUrl, SecretStr

from keeper.utils import format_utc_datetime

from ._urls import url_for_build, url_for_edition, url_for_task

if TYPE_CHECKING:
    import celery

    from keeper.models import Build, Edition


class AuthTokenResponse(BaseModel):
    """The auth token resource."""

    token: SecretStr
    """Token string. Use this token in the basic auth "username" field."""

    class Config:
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None,
        }


class RootLinks(BaseModel):
    """Sub-resource containing links to APIs."""

    self: HttpUrl
    """The URL of this resource."""

    token: HttpUrl
    """The URL of the authorization endpoint to obtain a token."""

    products: HttpUrl
    """The endpoint for the products listing."""


class RootData(BaseModel):
    """Sub-resource providing metadata about the service."""

    server_version: str
    """The service vesion."""

    documentation: HttpUrl
    """The URL of the service's documentation."""

    message: str
    """Description of the service."""


class RootResponse(BaseModel):
    """The root endpoint resources provides metadata and links for the
    service.
    """

    data: RootData

    links: RootLinks


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
            "product_url": build.product.get_url(),
            "slug": build.slug,
            "date_created": build.date_created,
            "date_ended": build.date_ended,
            "uploaded": build.uploaded,
            "bucket_name": build.product.bucket_name,
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
        obj: Dict[str, Any] = {
            "self_url": url_for_edition(edition),
            "product_url": edition.product.get_url(),
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
            "tracked_refs": (
                edition.tracked_refs
                if edition.mode_name == "git_refs"
                else None
            ),
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
