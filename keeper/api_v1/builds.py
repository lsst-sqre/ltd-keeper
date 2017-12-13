"""API v1 routes for builds."""

import uuid
from flask import jsonify, request, current_app

from . import api
from .. import db
from ..auth import token_auth, permission_required, is_authorized
from ..models import Product, Build, Edition, Permission
from ..utils import auto_slugify_edition
from ..logutils import log_route
from ..dasher import build_dashboard_safely


@api.route('/products/<slug>/builds/', methods=['POST'])
@log_route()
@token_auth.login_required
@permission_required(Permission.UPLOAD_BUILD)
def new_build(slug):
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
    surrogate_key = uuid.uuid4().hex
    build = Build(product=product, surrogate_key=surrogate_key)
    try:
        build.import_data(request.json)
        db.session.add(build)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # As a bonus, create an edition to track this Git ref set
    edition_count = Edition.query\
        .filter(Edition.product == product)\
        .filter(Edition.tracked_refs == build.git_refs)\
        .count()
    if edition_count == 0 and is_authorized(Permission.ADMIN_EDITION):
        try:
            edition_slug = auto_slugify_edition(build.git_refs)
            edition = Edition(product=product)
            edition.import_data(
                {'tracked_refs': build.git_refs,
                 'slug': edition_slug,
                 'title': edition_slug})
            db.session.add(edition)
            db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify(build.export_data()), 201, {'Location': build.get_url()}


@api.route('/builds/<int:id>', methods=['PATCH'])
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
    build.patch_data(request.json)
    db.session.commit()
    build_dashboard_safely(current_app, request, build.product)
    return jsonify({}), 200, {'Location': build.get_url()}


@api.route('/builds/<int:id>', methods=['DELETE'])
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


@api.route('/products/<slug>/builds/', methods=['GET'])
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
    build_urls = [build.get_url() for build in
                  Build.query.join(Product,
                                   Product.id == Build.product_id)
                  .filter(Product.slug == slug)
                  .filter(Build.date_ended == None).all()]  # NOQA
    return jsonify({'builds': build_urls})


@api.route('/builds/<int:id>', methods=['GET'])
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
