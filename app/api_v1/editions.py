"""API v1 routes for Editions."""

from flask import jsonify, request

from . import api
from .. import db
from ..auth import token_auth, permission_required
from ..models import Product, Edition, Permission


@api.route('/products/<slug>/editions/', methods=['POST'])
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def new_edition(slug):
    """Create a new Edition for a Product.

    **Authorization**

    User must be authenticated and have ``admin_edition`` permissions.

    **Example request**

    .. code-block:: http

       POST /products/lsst_apps/editions/ HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKcFlYUWlPakUwTlRZM056SXpORGdzSW1WNGNDSTZNVFEx...
       Connection: keep-alive
       Content-Length: 150
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "build_url": "http://localhost:5000/builds/1",
           "slug": "latest",
           "title": "Latest",
           "tracked_refs": [
               "master"
           ]
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 201 CREATED
       Content-Length: 2
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:29 GMT
       Location: http://localhost:5000/editions/1
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param slug: Product slug.

    :<json string build_url: URL of the build entity this Edition uses.
    :<json string slug: URL-safe name for edition.
    :<json string title: Human-readable name for edition.
    :<json array tracked_refs: Git ref(s) that describe the version of the
        Product that this this Edition is intended to point to. For
        multi-package documentation builds this is a list of Git refs that
        are checked out, in order of priority, for each component repository.

    :resheader Location: URL of the created Edition resource.

    :statuscode 201: No errors.
    :statuscode 404: Product not found.
    """
    product = Product.query.filter_by(slug=slug).first_or_404()
    edition = Edition(product=product)
    try:
        edition.import_data(request.json)
        db.session.add(edition)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({}), 201, {'Location': edition.get_url()}


@api.route('/editions/<int:id>', methods=['DELETE'])
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def deprecate_edition(id):
    """Deprecate an Edition of a Product.

    When an Edition is deprecated, the current time is added to the
    Edition's ``date_ended`` field. Any Edition record with a non-``null``
    ``date_ended`` field will be garbage-collected by LTD Keeper (the
    deletion does not occur immediately upon API request).

    **Authorization**

    User must be authenticated and have ``admin_edition`` permissions.

    **Example request**

    .. code-block:: http

       DELETE /editions/1 HTTP/1.1
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
       Date: Tue, 01 Mar 2016 17:21:30 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {}

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: Edition id.

    :statuscode 200: No errors.
    :statuscode 404: Edition not found.
    """
    edition = Edition.query.get_or_404(id)
    edition.deprecate()
    db.session.commit()
    return jsonify({}), 200


@api.route('/products/<slug>/editions/', methods=['GET'])
def get_product_editions(slug):
    """List all editions published for a Product.

    **Example request**

    .. code-block:: http

       GET /products/lsst_apps/editions/ HTTP/1.1

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 62
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 18:50:19 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "editions": [
               "http://localhost:5000/editions/1"
           ]
       }

    :param slug: Slug of the Product.

    :>json array editions: List of URLs of Edition entities for this Product.

    :statuscode 200: No errors.
    :statuscode 404: Product not found.
    """
    edition_urls = [edition.get_url() for edition in
                    Edition.query.join(Product,
                                       Product.id == Edition.product_id)
                    .filter(Product.slug == slug)
                    .filter(Edition.date_ended == None).all()]  # NOQA
    return jsonify({'editions': edition_urls})


@api.route('/editions/<int:id>', methods=['GET'])
def get_edition(id):
    """Show metadata for an Edition.

    **Example request**

    .. code-block:: http

       GET /editions/1 HTTP/1.1

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 413
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 18:50:18 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "build_url": "http://localhost:5000/builds/1",
           "date_created": "2016-03-01T11:50:18.196724Z",
           "date_ended": null,
           "date_rebuilt": "2016-03-01T11:50:18.196706Z",
           "product_url": "http://localhost:5000/products/lsst_apps",
           "published_url": "pipelines.lsst.io",
           "self_url": "http://localhost:5000/editions/1",
           "slug": "latest",
           "title": "Development master",
           "tracked_refs": [
               "master"
           ]
       }

    :param id: ID of the Edition.

    :>json string build_url: URL of the build entity this Edition uses.
    :>json string date_created: UTC date time when the edition was created.
    :>json string date_ended: UTC date time when the edition was deprecated;
        will be ``null`` for editions that are *not deprecated*.
    :>json string date_rebuilt: UTC date time when the edition last re-pointed
        to a different build.
    :>json string product_url: URL of parent product entity.
    :>json string published_url: Full URL where this edition is published.
    :>json string self_url: URL of this Edition entity.
    :>json string slug: URL-safe name for edition.
    :>json string title: Human-readable name for edition.
    :>json string tracked_refs: Git ref that this Edition points to. For multi-
        repository builds, this can be a comma-separated list of refs to use,
        in order of priority.

    :statuscode 200: No errors.
    :statuscode 404: Edition not found.
    """
    return jsonify(Edition.query.get_or_404(id).export_data())


@api.route('/editions/<int:id>', methods=['PATCH'])
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def edit_edition(id):
    """Edit an Edition.

    This PATCH method allows you to specify a subset of JSON fields to replace
    existing fields in the Edition resource. Not all fields in an Edition are
    editable via the API. See the allowed JSON fields below.

    Use :http:delete:`/editions/(int:id)` to deprecate an edition.

    The full resource record is returned.

    **Authorization**

    User must be authenticated and have ``admin_edition`` permissions.

    **Example request**

    .. code-block:: http

       PATCH /editions/1 HTTP/1.1
       Accept: application/json
       Accept-Encoding: gzip, deflate
       Authorization: Basic ZXlKcFlYUWlPakUwTlRZM056SXpORGdzSW1WNGNDSTZNVFEx...
       Connection: keep-alive
       Content-Length: 31
       Content-Type: application/json
       Host: localhost:5000
       User-Agent: HTTPie/0.9.3

       {
           "title": "Development master"
       }

    **Example response**

    .. code-block:: http

       HTTP/1.0 200 OK
       Content-Length: 413
       Content-Type: application/json
       Date: Tue, 01 Mar 2016 17:21:29 GMT
       Server: Werkzeug/0.11.3 Python/3.5.0

       {
           "build_url": "http://localhost:5000/builds/2",
           "date_created": "2016-03-01T10:21:29.017615Z",
           "date_ended": null,
           "date_rebuilt": "2016-03-01T10:21:29.590839Z",
           "product_url": "http://localhost:5000/products/lsst_apps",
           "published_url": "pipelines.lsst.io",
           "self_url": "http://localhost:5000/editions/1",
           "slug": "latest",
           "title": "Development master",
           "tracked_refs": [
               "master"
           ]
       }

    :reqheader Authorization: Include the token in a username field with a
        blank password; ``<token>:``.
    :param id: ID of the Edition.

    :<json string build_url: URL of the build entity this Edition uses
        (optional). Effectively this 'rebuilds' the edition.
    :<json string title: Human-readable name for edition (optional).
    :<json string slug: URL-safe name for edition (optinal). Changing the slug
        dynamically updates the ``published_url``.
    :<json array tracked_refs: Git ref(s) that this Edition points to.
        For multi-package documentation builds this is a list of Git refs that
        are checked out, in order of priority, for each component repository
        (optional).

    :>json string build_url: URL of the build entity this Edition uses.
    :>json string date_created: UTC date time when the edition was created.
    :>json string date_ended: UTC date time when the edition was deprecated;
        will be ``null`` for editions that are *not deprecated*.
    :>json string date_rebuilt: UTC date time when the edition last re-pointed
        to a different build.
    :>json string product_url: URL of parent product entity.
    :>json string published_url: Full URL where this edition is published.
    :>json string self_url: URL of this Edition entity.
    :>json string slug: URL-safe name for edition.
    :>json string title: Human-readable name for edition.
    :>json string tracked_refs: Git ref that this Edition points to. For multi-
        repository builds, this can be a comma-separated list of refs to use,
        in order of priority.

    :statuscode 200: No errors.
    :statuscode 404: Edition resource not found.
    """
    edition = Edition.query.get_or_404(id)
    try:
        edition.patch_data(request.json)
        db.session.add(edition)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(edition.export_data())
