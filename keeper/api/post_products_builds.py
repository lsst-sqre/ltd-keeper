"""The POST /products/<slug>/builds/ endpoint."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from flask import current_app, request
from flask_accept import accept_fallback
from structlog import get_logger

from keeper.api import api
from keeper.auth import is_authorized, permission_required, token_auth
from keeper.logutils import log_route
from keeper.mediatypes import v2_json_type
from keeper.models import Build, Edition, Permission, Product, db
from keeper.s3 import (
    format_bucket_prefix,
    open_s3_session,
    presign_post_url_for_directory_object,
    presign_post_url_for_prefix,
)
from keeper.taskrunner import (
    append_task_to_chain,
    launch_task_chain,
    mock_registry,
)
from keeper.tasks.dashboardbuild import build_dashboard
from keeper.utils import auto_slugify_edition

from ._models import BuildResponse
from ._urls import url_for_build, url_for_edition, url_for_product

if TYPE_CHECKING:
    import boto3
    from celery import Task

__all__ = ["post_products_builds_v1", "post_products_builds_v2"]

# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.api.post_products_builds.launch_task_chain",
        "keeper.api.post_products_builds.append_task_to_chain",
    ]
)


@api.route("/products/<slug>/builds/", methods=["POST"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.UPLOAD_BUILD)
def post_products_builds_v1(slug: str) -> Tuple[str, int, Dict[str, str]]:
    """Add a new build for a product.

    This method only adds a record for the build and specifies where the build
    should be uploaded. The client is reponsible for uploading the build.
    Once the documentation is uploaded, send
    :http:patch:`/builds/(int:id)` to set the 'uploaded' field to ``True``.

    If the user also has ``admin_edition`` permissions, this method will also
    create an edition that tracks this build's ``git_refs`` (if they are not
    already tracked). The slug and title of this edition are automatically
    derived from the build's ``git_refs``.

    **Authorization**

    User must be authenticated and have ``upload_build`` permissions.

    **Example request**

    .. code-block:: http

       POST /products/lsst_apps/builds/ HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKcFlYUWlPakUwTlRZM056SXpORGdzSW1WNGNDSTZNVFEx...
       Connection: keep-alive
       Content-Length: 74
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "git_refs": [
               "master"
           ],
           "github_requester": "jonathansick",
           "slug": "b1"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 201 CREATED
       Content-Length: 368
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:27 GMT
       Location: http://localhost:5000/builds/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "bucket_name": "an-s3-bucket",
           "bucket_root_dir": "lsst_apps/builds/b1",
           "date_created": "2016-03-01T10:21:27.583795Z",
           "date_ended": null,
           "git_refs": [
               "master"
           ],
           "github_requester": "jonathansick",
           "product_url": "http://localhost:5000/products/lsst_apps",
           "self_url": "http://localhost:5000/builds/1",
           "slug": "b1",
           "surrogate_key": "d290d35e579141e889e954a0b1f8b611",
           "uploaded": false
       }

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param slug: Product slug.

    :<json array git_refs: Git ref array that describes the version of the
        documentation being built. Typically this array will be a single
        string, e.g. ``['master']`` but may be a list of several refs for
        multi-package builds with ltd-mason.
    :<json github_requester: Optional GitHub username handle of person
        who triggered the build.
    :<json string slug: Optional URL-safe slug for the build. If a slug is
        not specified, then one will automatically be specified.

    :>json string bucket_name: Name of the S3 bucket hosting the built
        documentation.
    :>json string bucket_root_dir: Directory (path prefix) in the S3 bucket
        where this documentation build is located.
    :>json string date_created: UTC date time when the build was created.
    :>json string date_ended: UTC date time when the build was deprecated;
        will be ``null`` for builds that are *not deprecated*.
    :>json array git_refs: Git ref array that describes the version of the
        documentation being built. Typically this array will be a single
        string, e.g. ``['master']`` but may be a list of several refs for
        multi-package builds with ltd-mason.
    :>json string github_requester: GitHub username handle of person
        who triggered the build (null is not available).
    :>json string product_url: URL of parent product entity.
    :>json string self_url: URL of this build entity.
    :>json string slug: Slug of build; URL-safe slug. Will be unique to the
        Product.
    :>json string surrogate_key: The surrogate key attached to the headers
        of all files on S3 belonging to this build. This allows LTD Keeper
        to notify Fastly when an Edition is being re-pointed to a new build.
        The client is responsible for uploading files with this value as
        the ``x-amz-meta-surrogate-key`` value.
    :>json bool uploaded: True if the built documentation has been uploaded
        to the S3 bucket. Use :http:patch:`/builds/(int:id)` to
        set this to `True`.

    :resheader Location: URL of the created build.

    :statuscode 201: No error.
    :statuscode 404: Product not found.
    """
    build, task = _handle_new_build_for_product_slug(slug)

    build_response = BuildResponse.from_build(build, task=task)
    build_url = url_for_build(build)
    return build_response.json(), 201, {"Location": build_url}


@post_products_builds_v1.support(v2_json_type)
@log_route()
@token_auth.login_required
@permission_required(Permission.UPLOAD_BUILD)
def post_products_builds_v2(slug: str) -> Tuple[str, int, Dict[str, str]]:
    """Handle POST /products/../builds/ (version 2)."""
    logger = get_logger(__name__)

    build, task = _handle_new_build_for_product_slug(slug)

    # Create the presigned post URL or URLs for each declared directory
    # prefix
    request_data = request.get_json()
    if "directories" in request_data:
        directories = []
        for d in request_data["directories"]:
            d = d.strip()
            if not d.endswith("/"):
                d = f"{d}/"
            directories.append(d)
    else:
        directories = ["/"]

    logger.info("Creating presigned POST URLs", dirnames=directories)
    s3_session = open_s3_session(
        key_id=current_app.config["AWS_ID"],
        access_key=current_app.config["AWS_SECRET"],
    )
    presigned_prefix_urls = {}
    presigned_dir_urls = {}
    for d in set(directories):
        bucket_prefix = format_bucket_prefix(build.bucket_root_dirname, d)
        dir_key = bucket_prefix.rstrip("/")

        presigned_prefix_url = _create_presigned_url_for_prefix(
            s3_session=s3_session,
            bucket_name=build.product.bucket_name,
            prefix=bucket_prefix,
            surrogate_key=build.surrogate_key,
        )
        presigned_prefix_urls[d] = deepcopy(presigned_prefix_url)

        presigned_dir_url = _create_presigned_url_for_directory(
            s3_session=s3_session,
            bucket_name=build.product.bucket_name,
            key=dir_key,
            surrogate_key=build.surrogate_key,
        )
        presigned_dir_urls[d] = deepcopy(presigned_dir_url)

    logger.info(
        "Created presigned POST URLs for prefixes",
        post_urls=presigned_prefix_urls,
    )
    logger.info(
        "Created presigned POST URLs for dirs", post_urls=presigned_dir_urls
    )

    build_response = BuildResponse.from_build(
        build,
        task=task,
        post_prefix_urls=presigned_prefix_urls,
        post_dir_urls=presigned_dir_urls,
    )
    build_url = url_for_build(build)

    return build_response.json(), 201, {"Location": build_url}


def _handle_new_build_for_product_slug(
    product_slug: str,
) -> Tuple[Build, Task]:
    """Generic handler for ``POST /products/../builds/`` that creates a new
    build for a product.

    Parameters
    ----------
    product_slug : `str`
        The slug of the product that the build is being registered for.

    Returns
    -------
    build
        The build instance.
    task
        The *launched* celery task chain.
    """
    product = Product.query.filter_by(slug=product_slug).first_or_404()
    product_url = url_for_product(product)  # load for dashboard build

    build = _create_build(product)
    # As a bonus, create an edition to track this Git ref set
    _create_edition(product, build)

    # Run the task queue
    append_task_to_chain(build_dashboard.si(product_url))
    task = launch_task_chain()

    return build, task


def _create_build(product: Product) -> Build:
    """Create a build for a product."""
    surrogate_key = uuid.uuid4().hex
    build = Build(product=product, surrogate_key=surrogate_key)
    try:
        build.import_data(request.json)

        db.session.add(build)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return build


def _create_edition(product: Product, build: Build) -> Optional[Edition]:
    """Create an edition to track the Git ref of a build, if not tracking
    edition already exists.
    """
    logger = get_logger(__name__)

    edition = None

    edition_count = (
        Edition.query.filter(Edition.product == product)
        .filter(Edition.tracked_refs == build.git_refs)
        .count()
    )
    if edition_count == 0 and is_authorized(Permission.ADMIN_EDITION):
        try:
            edition_slug = auto_slugify_edition(build.git_refs)
            edition = Edition(product=product)
            edition.import_data(
                {
                    "tracked_refs": build.git_refs,
                    "slug": edition_slug,
                    "title": edition_slug,
                }
            )
            db.session.add(edition)
            db.session.commit()

            logger.info(
                "Created edition because of a build",
                url=url_for_edition(edition),
                id=edition.id,
                tracked_refs=edition.tracked_refs,
            )
        except Exception:
            logger.exception("Error while automatically creating an edition")
            db.session.rollback()
    else:
        logger.info(
            "Did not create a new edition because of a build",
            authorized=is_authorized(Permission.ADMIN_EDITION),
            edition_count=edition_count,
        )

    return edition


def _create_presigned_url_for_prefix(
    *,
    s3_session: boto3.session.Session,
    bucket_name: str,
    prefix: str,
    surrogate_key: str,
) -> Dict[str, Any]:
    # These conditions become part of the URL's presigned policy
    url_conditions = [
        {"acl": "public-read"},
        {"Cache-Control": "max-age=31536000"},
        # Make sure the surrogate-key is always consistent
        {"x-amz-meta-surrogate-key": surrogate_key},
        # Allow any Content-Type header
        ["starts-with", "$Content-Type", ""],
        # This is the default. It means for a success (204), no content
        # is returned by S3. This is what we want.
        {"success_action_status": "204"},
    ]
    # These fields are pre-populated for clients
    url_fields = {
        "acl": "public-read",
        "Cache-Control": "max-age=31536000",
        "x-amz-meta-surrogate-key": surrogate_key,
        "success_action_status": "204",
    }
    return presign_post_url_for_prefix(
        s3_session=s3_session,
        bucket_name=bucket_name,
        prefix=prefix,
        expiration=3600,
        conditions=url_conditions,
        fields=url_fields,
    )


def _create_presigned_url_for_directory(
    *,
    s3_session: boto3.session.Session,
    bucket_name: str,
    key: str,
    surrogate_key: str,
) -> Dict[str, Any]:
    # These conditions become part of the URL's presigned policy
    url_conditions = [
        {"acl": "public-read"},
        {"Cache-Control": "max-age=31536000"},
        # Make sure the surrogate-key is always consistent
        {"x-amz-meta-surrogate-key": surrogate_key},
        # This is the default. It means for a success (204), no content
        # is returned by S3. This is what we want.
        {"success_action_status": "204"},
    ]
    url_fields = {
        "acl": "public-read",
        "Cache-Control": "max-age=31536000",
        "x-amz-meta-surrogate-key": surrogate_key,
        "success_action_status": "204",
    }
    return presign_post_url_for_directory_object(
        s3_session=s3_session,
        bucket_name=bucket_name,
        key=key,
        fields=url_fields,
        conditions=url_conditions,
        expiration=3600,
    )
