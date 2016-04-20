"""API v1 routes for products."""

from flask import jsonify, request
from . import api
from .. import db
from ..auth import token_auth, permission_required
from ..models import Product, Permission


@api.route('/products/', methods=['GET'])
def get_products():
    """List all documentation products (anonymous access allowed).

    **Example request**

    .. code-block:: http

       GET /products/ HTTP/1.1

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 122
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:27 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "products": [
               "http://localhost:5000/products/lsst_apps",
               "http://localhost:5000/products/qserv_distrib"
           ]
       }

    :>json array products: List of product URLs.

    :statuscode 200: No error.
    """
    return jsonify({'products': [product.get_url() for product in
                                 Product.query.all()]})


@api.route('/products/<slug>', methods=['GET'])
def get_product(slug):
    """Get the record of a single documentation product (anonymous access
    allowed).

    **Example request**

    .. code-block:: http

       GET /products/pipelines HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbVY0Y0NJNk1UUTJNVEV3...
       Connection: keep-alive
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 385
       Content-Type: application/json
       Date: Tue, 19 Apr 2016 21:17:52 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "bucket_name": "an-s3-bucket",
           "doc_repo": "https://github.com/lsst/pipelines_docs.git",
           "domain": "pipelines.lsst.io",
           "fastly_domain": "pipelines.lsst.io.global.ssl.fastly.net",
           "root_domain": "lsst.io",
           "root_fastly_domain": "global.ssl.fastly.net",
           "self_url": "http://localhost:5000/products/pipelines",
           "slug": "pipelines",
           "title": "LSST Science Pipelines"
       }

    :param slug: Identifier for this product.

    :>json string bucket_name: Name of the S3 bucket hosting builds.
    :>json string doc_repo: URL of the Git documentation repo (i.e., on
       GitHub).
    :>json string domain: Full domain where this product's documentation
       is served from this LSST the Docs installation is served from.
       (e.g., ``pipelines.lsst.io``).
    :>json string fastly_domain: Full domain where Fastly serves content
       for this product. Note that ``domain`` is CNAME'd to ``fastly_domain``.
    :>json string root_domain: Root domain name where documentation for
       this LSST the Docs installation is served from. (e.g., ``lsst.io``).
    :>json string root_fastly_domain: Root domain name for Fastly CDN used
       by this LSST the Docs installation.
    :>json string self_url: URL of this Product resource.
    :>json string slug: URL/path-safe identifier for this product.
    :>json string title: Human-readable product title.

    :statuscode 200: No error.
    :statuscode 404: Product not found.
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    return jsonify(product.export_data())


@api.route('/products/', methods=['POST'])
@permission_required(Permission.ADMIN_PRODUCT)
@token_auth.login_required
def new_product():
    """Create a new documentation product.

    **Authorization**

    User must be authenticated and have ``admin_product`` permissions.

    **Example request**

    .. code-block:: http

       POST /products/ HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbVY0Y0NJNk1UUTJNVEV3...
       Connection: keep-alive
       Content-Length: 218
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "bucket_name": "an-s3-bucket",
           "doc_repo": "https://github.com/lsst/pipelines_docs.git",
           "root_domain": "lsst.io",
           "root_fastly_domain": "global.ssl.fastly.net",
           "slug": "pipelines",
           "title": "LSST Science Pipelines"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 201 CREATED
       Content-Length: 2
       Content-Type: application/json
       Date: Tue, 19 Apr 2016 21:17:52 GMT
       Location: http://localhost:5000/products/pipelines
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.

    :<json string bucket_name: Name of the S3 bucket hosting builds.
    :<json string doc_repo: URL of the Git documentation repo (i.e., on
       GitHub).
    :<json string root_domain: Root domain name where documentation for
       this LSST the Docs installation is served from. (e.g., ``lsst.io``).
    :<json string root_fastly_domain: Root domain name for Fastly CDN used
       by this LSST the Docs installation.
    :<json string self_url: URL of this Product resource.
    :<json string slug: URL/path-safe identifier for this product. The slug
       is validated against the regular expression ``^[a-z]([-]*[a-z0-9])*$``.
    :<json string title: Human-readable product title.

    :resheader Location: URL of the created product.

    :statuscode 201: No error.
    """
    product = Product()
    try:
        product.import_data(request.json)
        db.session.add(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({}), 201, {'Location': product.get_url()}


@api.route('/products/<slug>', methods=['PATCH'])
@permission_required(Permission.ADMIN_PRODUCT)
@token_auth.login_required
def edit_product(slug):
    """Update a product.

    Note that not all fields can be updated with this method (currently).
    See below for updateable fields. Contact the operator to update the slug,
    bucket name, or Fastly domain.

    **Authorization**

    User must be authenticated and have ``admin_product`` permissions.

    **Example request**

    .. code-block:: http

       PATCH /products/qserv HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKaGJHY2lPaUpJVXpJMU5pSXNJbVY0Y0NJNk1UUTJNVEV3...
       Connection: keep-alive
       Content-Length: 30
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "title": "Qserv Data Access"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 2
       Content-Type: application/json
       Date: Tue, 19 Apr 2016 21:17:53 GMT
       Location: http://localhost:5000/products/qserv
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param slug: Product slug.

    :<json string doc_repo: URL of the Git documentation repo (i.e., on
       GitHub) (optional).
    :<json string title: Human-readable product title (optional).

    :resheader Location: URL of the created product.

    :statuscode 200: No error.
    :statuscode 404: Product not found.
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    try:
        product.patch_data(request.json)
        db.session.add(product)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({}), 200, {'Location': product.get_url()}
