"""API v1 routes for builds."""

from flask import jsonify, request
from flask_accept import accept_fallback

from ..auth import permission_required, token_auth
from ..logutils import log_route
from ..models import Build, Permission, Product, db
from ..taskrunner import (
    append_task_to_chain,
    insert_task_url_in_response,
    launch_task_chain,
    mock_registry,
)
from ..tasks.dashboardbuild import build_dashboard
from . import api

# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.api.builds.launch_task_chain",
        "keeper.api.builds.append_task_to_chain",
    ]
)


@api.route("/builds/<int:id>", methods=["PATCH"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.UPLOAD_BUILD)
def patch_build(id):
    """Mark a build as uploaded.

    This method should be called when the documentation has been successfully
    uploaded to the S3 bucket, setting the 'uploaded' field to ``True``.

    **Authorization**

    User must be authenticated and have ``upload_build`` permissions.

    **Example request**

    .. code-block:: http

       PATCH /builds/1 HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKcFlYUWlPakUwTlRZM056SXpORGdzSW1WNGNDSTZNVFEx...
       Connection: keep-alive
       Content-Length: 18
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "uploaded": true
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 2
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:28 GMT
       Location: http://localhost:5000/builds/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the build.
    :<json bool uploaded: True if the built documentation has been uploaded
        to the S3 bucket.

    :resheader Location: URL of the created build.

    :statuscode 200: No error.
    :statuscode 404: Build not found.
    """
    build = Build.query.get_or_404(id)
    try:
        build.patch_data(request.json)
        build_url = build.get_url()
        db.session.commit()

        # Run the task queue
        append_task_to_chain(build_dashboard.si(build.product.get_url()))
        task = launch_task_chain()
        response = insert_task_url_in_response({}, task)
    except Exception:
        db.session.rollback()
        raise
    return jsonify(response), 200, {"Location": build_url}


@api.route("/builds/<int:id>", methods=["DELETE"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.DEPRECATE_BUILD)
def deprecate_build(id):
    """Mark a build as deprecated.

    **Authorization**

    User must be authenticated and have ``deprecate_build`` permissions.

    **Example request**

    .. code-block:: http

       DELETE /builds/1 HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKcFlYUWlPakUwTlRZM056SXpORGdzSW1WNGNDSTZNVFEx...
       Connection: keep-alive
       Content-Length: 0
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 2
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:29 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the build.

    :statuscode 200: No error.
    :statuscode 404: Build not found.
    """
    build = Build.query.get_or_404(id)
    build.deprecate_build()
    db.session.commit()
    return jsonify({}), 200


@api.route("/products/<slug>/builds/", methods=["GET"])
@accept_fallback
@log_route()
def get_product_builds(slug):
    """List all builds for a product.

    **Example request**

    .. code-block:: http

       GET /products/lsst_apps/builds/ HTTP/1.1

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 96
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:28 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "builds": [
               "http://localhost:5000/builds/1",
               "http://localhost:5000/builds/2"
           ]
       }

    :param slug: Slug of the Product.

    :>json array builds: List of URLs of Build entities for this product.

    :statuscode 200: No error.
    :statuscode 404: Product not found.
    """
    build_urls = [
        build.get_url()
        for build in Build.query.join(Product, Product.id == Build.product_id)
        .filter(Product.slug == slug)
        .filter(Build.date_ended is None)
        .all()
    ]  # NOQA
    return jsonify({"builds": build_urls})


@api.route("/builds/<int:id>", methods=["GET"])
@accept_fallback
@log_route()
def get_build(id):
    """Show metadata for a single build.

    **Example request**

    .. code-block:: http

       GET /builds/1 HTTP/1.1

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 367
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:28 GMT
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
           "uploaded": true
       }

    :param id: ID of the Build.

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
    :>json string slug: slug of build; URL-safe slug.
    :>json string product_url: URL of parent product entity.
    :>json string published_url: Full URL where this build is published to
        the reader.
    :>json string self_url: URL of this build entity.
    :>json string surrogate_key: The surrogate key attached to the headers
        of all files on S3 belonging to this build. This allows LTD Keeper
        to notify Fastly when an Edition is being re-pointed to a new build.
        The client is responsible for uploading files with this value as
        the ``x-amz-meta-surrogate-key`` value.
    :>json bool uploaded: True if the built documentation has been uploaded
        to the S3 bucket. Use :http:patch:`/builds/(int:id)` to
        set this to `True`.

    :statuscode 200: No error.
    :statuscode 404: Build not found.
    """
    return jsonify(Build.query.get_or_404(id).export_data())
