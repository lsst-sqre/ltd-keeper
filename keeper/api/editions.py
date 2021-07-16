"""API v1 routes for Editions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.logutils import log_route
from keeper.models import Edition, Permission, Product, db
from keeper.taskrunner import (
    append_task_to_chain,
    launch_task_chain,
    mock_registry,
)
from keeper.tasks.dashboardbuild import build_dashboard

from ._models import EditionResponse, EditionUrlListingResponse, QueuedResponse
from ._urls import url_for_edition

if TYPE_CHECKING:
    from flask import Response

# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.api.editions.launch_task_chain",
        "keeper.api.editions.append_task_to_chain",
    ]
)


@api.route("/products/<slug>/editions/", methods=["POST"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def new_edition(slug: str) -> Tuple[str, int, Dict[str, str]]:
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
           "mode:": "git_refs",
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
    :<json string slug: URL-safe name for edition. Don't include this field
        when using ``autoincrement: true``.
    :<json string title: Human-readable name for edition.
    :<json str mode: Tracking mode.
       ``git_refs``: track the Git ref specified by ``tracked_refs``.
       ``lsst_doc``: track LSST document version tags.
    :<json array tracked_refs: Git ref(s) that describe the version of the
        Product that this this Edition is intended to point to when using
        the ``git_refs`` tracking mode.
    :<json bool autoincrement: Instead of providing a ``slug``, the server
        automatically assigns an integer slug that is one larger than
        existing slug integers. Starts from ``1``.

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

        # Run the task queue
        append_task_to_chain(build_dashboard.si(product.get_url()))
        task = launch_task_chain()
    except Exception:
        db.session.rollback()
        raise

    response = EditionResponse.from_edition(edition, task=task)
    edition_url = url_for_edition(edition)

    return response.json(), 201, {"Location": edition_url}


@api.route("/editions/<int:id>", methods=["DELETE"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def deprecate_edition(id: int) -> Tuple[str, int]:
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

    append_task_to_chain(build_dashboard.si(edition.product.get_url()))
    task = launch_task_chain()

    response = QueuedResponse.from_task(task)
    return response.json(), 200


@api.route("/products/<slug>/editions/", methods=["GET"])
@accept_fallback
@log_route()
def get_product_editions(slug: str) -> Response:
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
    edition_urls = [
        url_for_edition(edition)
        for edition in Edition.query.join(
            Product, Product.id == Edition.product_id
        )
        .filter(Product.slug == slug)
        .filter(Edition.date_ended == None)  # noqa: E711
        .all()
    ]
    response = EditionUrlListingResponse(editions=edition_urls)
    return response.json()


@api.route("/editions/<int:id>", methods=["GET"])
@accept_fallback
@log_route()
def get_edition(id: int) -> str:
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
           "mode": "git_refs",
           "product_url": "http://localhost:5000/products/lsst_apps",
           "published_url": "pipelines.lsst.io",
           "self_url": "http://localhost:5000/editions/1",
           "slug": "latest",
           "surrogate_key": "2a5f38f27e3c46258fd9b0e69afe54fd",
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
    :>json str mode: Tracking mode.
       ``git_refs``: track the Git ref specified by ``tracked_refs``.
       ``lsst_doc``: track LSST document version tags.
    :>json string product_url: URL of parent product entity.
    :>json string published_url: Full URL where this edition is published.
    :>json string self_url: URL of this Edition entity.
    :>json string slug: URL-safe name for edition.
    :>json string surrogate_key: Surrogate key that should be used in the
        ``x-amz-meta-surrogate-control`` header of any the edition's S3
        objects to control Fastly caching.
    :>json string title: Human-readable name for edition.
    :>json string tracked_refs: Git ref that this Edition points to. For multi-
        repository builds, this can be a comma-separated list of refs to use,
        in order of priority.

    :statuscode 200: No errors.
    :statuscode 404: Edition not found.
    """
    edition = Edition.query.get_or_404(id)
    return EditionResponse.from_edition(edition).json()


@api.route("/editions/<int:id>", methods=["PATCH"])
@accept_fallback
@log_route()
@token_auth.login_required
@permission_required(Permission.ADMIN_EDITION)
def edit_edition(id: int) -> str:
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
           "mode": "git_refs",
           "product_url": "http://localhost:5000/products/lsst_apps",
           "published_url": "pipelines.lsst.io",
           "self_url": "http://localhost:5000/editions/1",
           "slug": "latest",
           "surrogate_key": "2a5f38f27e3c46258fd9b0e69afe54fd",
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
    :<json str mode: Tracking mode.
       ``git_refs``: track the Git ref specified by ``tracked_refs``.
       ``lsst_doc``: track LSST document version tags.
    :<json array tracked_refs: Git ref(s) that this Edition points to.
        For multi-package documentation builds this is a list of Git refs that
        are checked out, in order of priority, for each component repository
        (optional).
    :<json bool pending_rebuild: Semaphore indicating if a rebuild for the
        edition is currently queued (optional). This should only be set
        manually if the ``rebuild_edition`` task failed.

    :>json string build_url: URL of the build entity this Edition uses.
    :>json string date_created: UTC date time when the edition was created.
    :>json string date_ended: UTC date time when the edition was deprecated;
        will be ``null`` for editions that are *not deprecated*.
    :>json string date_rebuilt: UTC date time when the edition last re-pointed
        to a different build.
    :>json str mode: Tracking mode.
       ``git_refs``: track the Git ref specified by ``tracked_refs``.
       ``lsst_doc``: track LSST document version tags.
    :>json string product_url: URL of parent product entity.
    :>json string published_url: Full URL where this edition is published.
    :>json string self_url: URL of this Edition entity.
    :>json string slug: URL-safe name for edition.
    :>json string surrogate_key: Surrogate key that should be used in the
        ``x-amz-meta-surrogate-control`` header of any the edition's S3
        objects to control Fastly caching.
    :>json string title: Human-readable name for edition.
    :>json string tracked_refs: Git ref that this Edition points to, for use
        with the ``git_refs`` tricking mode. For multi-repository products,
        this can be a comma-separated list of refs to use, in order of
        priority.

    :statuscode 200: No errors.
    :statuscode 404: Edition resource not found.
    """
    edition = Edition.query.get_or_404(id)
    try:
        edition.patch_data(request.json)
        db.session.add(edition)
        db.session.commit()

        # Run the task queue
        append_task_to_chain(build_dashboard.si(edition.product.get_url()))
        task = launch_task_chain()
    except Exception:
        db.session.rollback()
        raise

    response = EditionResponse.from_edition(edition, task=task)
    return response.json()
