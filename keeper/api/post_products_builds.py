"""The POST /products/<slug>/builds/ endpoint."""

from __future__ import annotations

from typing import Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.logutils import log_route
from keeper.mediatypes import v2_json_type
from keeper.models import Permission, Product
from keeper.services.createbuild import (
    create_build,
    create_presigned_post_urls,
)

from ._models import BuildPostRequest, BuildPostRequestWithDirs, BuildResponse
from ._urls import url_for_build

__all__ = ["post_products_builds_v1", "post_products_builds_v2"]


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
    product = Product.query.filter_by(slug=slug).first_or_404()
    request_data = BuildPostRequest.parse_obj(request.json)

    build, edition = create_build(
        product=product,
        git_ref=request_data.git_refs[0],
        github_requester=request_data.github_requester,
        slug=request_data.slug,
    )

    build_response = BuildResponse.from_build(build=build)
    build_url = url_for_build(build)
    return build_response.json(), 201, {"Location": build_url}


@post_products_builds_v1.support(v2_json_type)
@log_route()
@token_auth.login_required
@permission_required(Permission.UPLOAD_BUILD)
def post_products_builds_v2(slug: str) -> Tuple[str, int, Dict[str, str]]:
    """Handle POST /products/../builds/ (version 2)."""
    product = Product.query.filter_by(slug=slug).first_or_404()
    request_data = BuildPostRequestWithDirs.parse_obj(request.json)

    build, edition = create_build(
        product=product,
        git_ref=request_data.git_refs[0],
        github_requester=request_data.github_requester,
        slug=request_data.slug,
    )

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
