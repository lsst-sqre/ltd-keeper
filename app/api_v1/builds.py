"""API v1 routes for builds."""

from datetime import datetime
from flask import jsonify, request

from . import api
from .. import db
from ..auth import token_auth
from ..models import Product, Build


@api.route('/products/<slug>/builds/', methods=['POST'])
@token_auth.login_required
def new_build(slug):
    """Add a new build for a product (token required).

    This method only adds a record for the build and specifies where the build
    should be uploaded. The client is reponsible for uploading the build.
    Once the documentation is uploaded, send
    :http:post:`/v1/builds/(int:id)/uploaded` to register that the doc
    has been uploaded.

    .. todo::

       Update examples.

    **Example request**

    .. code-block:: http

       POST /v1/products/1/builds/ HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKbGVIQWlPakUwTlRVd05qUXdNVElzSW1Gc1p5STZJa2hU...
       Connection: keep-alive
       Content-Length: 14
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "slug": "b1"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 201 OK
       Content-Length: 217
       Content-Type: application/json
       Date: Thu, 11 Feb 2016 17:39:32 GMT
       Location: http://localhost:5000/v1/builds/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "date_created": "2016-02-11T10:39:32.833623Z",
           "date_ended": null,
           "slug": "b1",
           "product_url": "http://localhost:5000/v1/products/1",
           "self_url": "http://localhost:5000/v1/builds/1",
           "uploaded": false
       }

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param slug: Product slug.

    :<json string slug: Optional URL-safe slug for the build. If a slug is
        not specified, then one will automatically be specified.
    :<json github_requester: Optional GitHub username handle of person
        who triggered the build.
    :<json array git_refs: Git ref array that describe the version of the
        documentation being built. Typically this array will be a single
        string, e.g. ``['master']`` but may be a list of several refs for
        multi-package builds with ltd-mason.

    :>json string bucket_name: Name of the S3 bucket hosting the built
        documentation.
    :>json string bucket_root_dir: Directory (path prefix) in the S3 bucket
        where this documentation build is located.
    :>json string date_created: UTC date time when the build was created.
    :>json string date_ended: UTC date time when the build was deprecated;
        will be ``null`` for builds are are *not deprecated*.
    :>json array git_refs: Git ref (or array of Git refs for multi-package
        builds with ltd-mason) that describe the version of the documentation.
    :>json string github_requester: GitHub username handle of person
        who triggered the build (null is not available).
    :>json string slug: slug of build; URL-safe slug.
    :>json string product_url: URL of parent product entity.
    :>json string self_url: URL of this build entity.
    :>json string uploaded: True if the built documentation has been uploaded
        to the S3 bucket. Use :http:post:`/v1/builds/(int:id)/uploaded` to
        set this to `True`.

    :resheader Location: URL of the created build.
    :statuscode 201: No error.
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    build = Build(product=product)
    try:
        build.import_data(request.json)
        db.session.add(build)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(build.export_data()), 201, {'Location': build.get_url()}


@api.route('/builds/<int:id>/uploaded', methods=['POST'])
@token_auth.login_required
def register_build_upload(id):
    """Mark a build as uploaded (token required).

    This method should be called when the documentation has been successfully
    uploaded to the S3 bucket.

    The ``uploaded`` field for the build record is changed to ``True``.

    **Example request**

    .. code-block:: http

       POST /v1/builds/1/uploaded HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbWxoZENJNk1UUTFOVEl4...
       Connection: keep-alive
       Content-Length: 0
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 202 ACCEPTED
       Content-Length: 2
       Content-Type: application/json
       Date: Thu, 11 Feb 2016 17:53:36 GMT
       Location: http://localhost:5000/v1/builds/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the build.
    :resheader Location: URL of the created build.
    :statuscode 202: No error.
    """
    build = Build.query.get_or_404(id)
    build.register_upload()
    db.session.commit()
    return jsonify({}), 202, {'Location': build.get_url()}


@api.route('/builds/<int:id>', methods=['DELETE'])
@token_auth.login_required
def deprecate_build(id):
    """Mark a build as deprecated (token required).

    **Example request**

    .. code-block:: http

       DELETE /v1/builds/1 HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKbGVIQWlPakUwTlRVeE16RTJOVFVzSW1Gc1p5STZJa2hU...
       Connection: keep-alive
       Content-Length: 0
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 202 ACCEPTED
       Content-Length: 2
       Content-Type: application/json
       Date: Wed, 10 Feb 2016 18:15:08 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the build.
    :statuscode 202: No error.
    """
    build = Build.query.get_or_404(id)
    build.date_ended = datetime.now()
    db.session.commit()
    return jsonify({}), 202


@api.route('/products/<slug>/builds/', methods=['GET'])
def get_product_builds(slug):
    """List all builds for a product.

    .. todo::

       Update example.

    **Example request**

    .. code-block:: http

       GET /v1/products/1/builds/ HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Connection: keep-alive
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 61
       Content-Type: application/json
       Date: Wed, 10 Feb 2016 17:40:16 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "builds": [
               "http://localhost:5000/v1/builds/1"
           ]
       }

    :param id: ID of the Product.
    :>json array builds: List of URLs of Build entities for this product.
    :statuscode 200: No error.
    """
    build_urls = [build.get_url() for build in
                  Build.query.filter(Product.slug == slug).all()]
    return jsonify({'builds': build_urls})


@api.route('/builds/<int:id>', methods=['GET'])
def get_build(id):
    """Show metadata for a single build.

    .. todo::

       Update examples.

    **Example request**

    .. code-block:: http

       GET /v1/builds/1 HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Connection: keep-alive
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 196
       Content-Type: application/json
       Date: Wed, 10 Feb 2016 17:48:16 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "date_created": "2016-02-09T17:28:14.941424Z",
           "date_ended": null,
           "slug": "b1",
           "product_url": "http://localhost:5000/v1/products/1",
           "self_url": "http://localhost:5000/v1/builds/1"
           "uploaded": false
       }

    :param id: ID of the Build.

    :>json string bucket_name: Name of the S3 bucket hosting the built
        documentation.
    :>json string bucket_root_dir: Directory (path prefix) in the S3 bucket
        where this documentation build is located.
    :>json string date_created: UTC date time when the build was created.
    :>json string date_ended: UTC date time when the build was deprecated;
        will be ``null`` for builds are are *not deprecated*.
    :>json array git_refs: Git ref (or array of Git refs for multi-package
        builds with ltd-mason) that describe the version of the documentation.
    :>json string github_requester: GitHub username handle of person
        who triggered the build (null is not available).
    :>json string slug: slug of build; URL-safe slug.
    :>json string product_url: URL of parent product entity.
    :>json string self_url: URL of this build entity.
    :>json string uploaded: True if the built documentation has been uploaded
        to the S3 bucket. Use :http:post:`/v1/builds/(int:id)/uploaded` to
        set this to `True`.

    :statuscode 200: No error.
    :statuscode 404: Build not found.
    """
    return jsonify(Build.query.get_or_404(id).export_data())
