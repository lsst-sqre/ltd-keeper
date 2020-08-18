"""API v1 routes for products."""

from flask import jsonify, request
from flask_accept import accept_fallback

from . import api
from ..models import db
from ..auth import token_auth, permission_required
from ..models import Product, Permission, Edition
from ..logutils import log_route
from ..tasks.dashboardbuild import build_dashboard
from ..taskrunner import (launch_task_chain, append_task_to_chain,
                          insert_task_url_in_response, mock_registry)


# Register imports of celery task chain launchers
mock_registry.extend([
    'keeper.api.products.launch_task_chain',
    'keeper.api.products.append_task_to_chain',
])


@api.route('/products/', methods=['GET'])
@accept_fallback
@log_route()
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
@accept_fallback
@log_route()
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
           "surrogate_key": "2a5f38f27e3c46258fd9b0e69afe54fd",
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
    :>json string published_url: Full URL where this product is published to
        the reader.
    :>json string self_url: URL of this Product resource.
    :>json string slug: URL/path-safe identifier for this product.
    :>json string surrogate_key: Surrogate key that should be used in the
        ``x-amz-meta-surrogate-control`` header of any product-level
        dashboards to control Fastly caching.
    :>json string title: Human-readable product title.

    :statuscode 200: No error.
    :statuscode 404: Product not found.
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    return jsonify(product.export_data())


@api.route('/products/', methods=['POST'])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def new_product():
    """Create a new documentation product.

    Every new product also includes a default edition (slug is 'main'). This
    main edition tracks the master branch by default. Fastly is configured to
    show this main edition at the product's root URL rather than in the /v/
    directory.

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
           "surrogate_key": "2a5f38f27e3c46258fd9b0e69afe54fd",
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
    :<json str main_mode: Tracking mode for the main (default) edition.
       ``git_refs``: track the ``master`` branch.
       ``lsst_doc``: track LSST document version tags.
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
        request_json = request.json
        product.import_data(request_json)
        db.session.add(product)
        db.session.flush()  # Because Edition._validate_slug does not autoflush

        # Create a default edition for the product
        edition_data = {'tracked_refs': ['master'],
                        'slug': 'main',
                        'title': 'Latest'}
        if 'main_mode' in request_json:
            edition_data['mode'] = request_json['main_mode']
        else:
            # Default tracking mode
            edition_data['mode'] = 'git_refs'

        edition = Edition(product=product)
        edition.import_data(edition_data)
        db.session.add(edition)

        db.session.commit()

        # Run the task queue
        append_task_to_chain(build_dashboard.si(product.get_url()))
        task = launch_task_chain()
        response = insert_task_url_in_response({}, task)
    except Exception:
        db.session.rollback()
        raise

    return jsonify(response), 201, {'Location': product.get_url()}


@api.route('/products/<slug>', methods=['PATCH'])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
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

        # Run the task queue
        append_task_to_chain(build_dashboard.si(product.get_url()))
        task = launch_task_chain()
        response = insert_task_url_in_response({}, task)
    except Exception:
        db.session.rollback()
        raise

    return jsonify(response), 200, {'Location': product.get_url()}


@api.route('/products/<slug>/dashboard', methods=['POST'])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def rebuild_product_dashboard(slug):
    """Rebuild the LTD Dasher dashboard manually for a single product.

    Note that the dashboard is built asynchronously.

    **Authorization**

    User must be authenticated and have ``admin_product`` permissions.

    :statuscode 202: Dashboard rebuild trigger sent.

    **See also**

    - :http:post:`/dashboards`
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    append_task_to_chain(build_dashboard.si(product.get_url()))
    task = launch_task_chain()
    response = insert_task_url_in_response({}, task)
    return jsonify(response), 202, {}
