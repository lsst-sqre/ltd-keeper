"""API v1 routes for builds."""

from datetime import datetime
from flask import jsonify, request

from . import api
from .. import db
from ..auth import token_auth
from ..models import Product, Build


@api.route('/products/<int:id>/builds/', methods=['POST'])
@token_auth.login_required
def new_build(id):
    """Add a new build for a product (token required).

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
           "name": "b1"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 201 CREATED
       Content-Length: 2
       Content-Type: application/json
       Date: Wed, 10 Feb 2016 00:28:14 GMT
       Location: http://localhost:5000/v1/builds/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the Product.
    :<json string name: Name of build; URL-safe slug.
    :resheader Location: URL of the created build.
    :statuscode 201: No error.
    """
    product = Product.query.get_or_404(id)
    build = Build(product=product)
    build.import_data(request.json)
    db.session.add(build)
    db.session.commit()
    return jsonify({}), 201, {'Location': build.get_url()}


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
    build.end_date = datetime.now()
    db.session.commit()
    return jsonify({}), 202


@api.route('/products/<int:id>/builds/', methods=['GET'])
def get_product_builds(id):
    """List all builds for a product.

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
    print(id)
    build_urls = [build.get_url() for build in
                  Build.query.filter(Build.product_id == id).all()]
    return jsonify({'builds': build_urls})


@api.route('/builds/<int:id>', methods=['GET'])
def get_build(id):
    """Show metadata for a single build.

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
           "name": "b1",
           "product_url": "http://localhost:5000/v1/products/1",
           "self_url": "http://localhost:5000/v1/builds/1"
       }

    :param id: ID of the Build.

    :>json string date_created: UTC date time when the build was created.
    :>json string date_ended: UTC date time when the build was deprecated;
        will be ``null`` for builds are are *not deprecated*.
    :>json string name: Name of build; URL-safe slug.
    :>json string product_url: URL of parent product entity.
    :>json string self_url: URL of this build entity.

    :statuscode 200: No error.
    :statuscode 404: Build not found.
    """
    return jsonify(Build.query.get_or_404(id).export_data())
