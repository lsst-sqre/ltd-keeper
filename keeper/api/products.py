"""API v1 routes for products."""

from __future__ import annotations

from typing import Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.logutils import log_route
from keeper.models import Organization, Permission, Product, db
from keeper.services.createproduct import create_product
from keeper.services.requestdashboardbuild import request_dashboard_build
from keeper.services.updateproduct import update_product
from keeper.taskrunner import launch_tasks

from ._models import (
    ProductPatchRequest,
    ProductPostRequest,
    ProductResponse,
    ProductUrlListingResponse,
    QueuedResponse,
)
from ._urls import url_for_product


@api.route("/products/", methods=["GET"])
@accept_fallback
@log_route()
def get_products() -> str:
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
    response = ProductUrlListingResponse(
        products=[url_for_product(product) for product in Product.query.all()]
    )
    return response.json()


@api.route("/products/<slug>", methods=["GET"])
@accept_fallback
@log_route()
def get_product(slug: str) -> str:
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
    default_org = Organization.query.order_by(Organization.id).first_or_404()
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == default_org.slug)
        .filter(Product.slug == slug)
        .first_or_404()
    )
    response = ProductResponse.from_product(product)
    return response.json()


@api.route("/products/", methods=["POST"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def new_product() -> Tuple[str, int, Dict[str, str]]:
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
    product_request = ProductPostRequest.parse_obj(request.json)

    # Get default organization (v1 API adapter for organizations)
    org = Organization.query.order_by(Organization.id).first_or_404()

    try:
        product, main_edition = create_product(
            org=org,
            slug=product_request.slug,
            doc_repo=product_request.doc_repo,
            title=product_request.title,
            default_edition_mode=(
                product_request.main_mode
                if product_request.main_mode is not None
                else None
            ),
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()

    response = ProductResponse.from_product(product, task=task)
    product_url = url_for_product(product)
    return response.json(), 201, {"Location": product_url}


@api.route("/products/<slug>", methods=["PATCH"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def edit_product(slug: str) -> Tuple[str, int, Dict[str, str]]:
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
    default_org = Organization.query.order_by(Organization.id).first_or_404()
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == default_org.slug)
        .filter(Product.slug == slug)
        .first_or_404()
    )
    request_data = ProductPatchRequest.parse_obj(request.json)

    try:
        product = update_product(
            product=product,
            new_doc_repo=request_data.doc_repo,
            new_title=request_data.title,
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()
    response = ProductResponse.from_product(product, task=task)
    product_url = url_for_product(product)
    return response.json(), 200, {"Location": product_url}


@api.route("/products/<slug>/dashboard", methods=["POST"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def rebuild_product_dashboard(slug: str) -> Tuple[str, int, Dict[str, str]]:
    """Rebuild the LTD Dasher dashboard manually for a single product.

    Note that the dashboard is built asynchronously.

    **Authorization**

    User must be authenticated and have ``admin_product`` permissions.

    :statuscode 202: Dashboard rebuild trigger sent.

    **See also**

    - :http:post:`/dashboards`
    """
    default_org = Organization.query.order_by(Organization.id).first_or_404()
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Organization.slug == default_org.slug)
        .filter(Product.slug == slug)
        .first_or_404()
    )
    request_dashboard_build(product)
    task = launch_tasks()
    response = QueuedResponse.from_task(task)
    return response.json(), 202, {}
