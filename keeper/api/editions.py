"""API v1 routes for Editions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Tuple

from flask import request
from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.logutils import log_route
from keeper.models import Edition, Organization, Permission, Product, db
from keeper.services.createedition import create_edition
from keeper.services.requestdashboardbuild import request_dashboard_build
from keeper.services.updateedition import update_edition
from keeper.taskrunner import launch_tasks

from ._models import (
    EditionPatchRequest,
    EditionPostRequest,
    EditionResponse,
    EditionUrlListingResponse,
    QueuedResponse,
)
from ._urls import build_from_url, url_for_edition

if TYPE_CHECKING:
    from keeper.models import Build


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
               "main"
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
    default_org = Organization.query.order_by(Organization.id).first_or_404()
    product = (
        Product.query.join(
            Organization, Organization.id == Product.organization_id
        )
        .filter(Product.slug == slug)
        .filter(Organization.slug == default_org.slug)
        .first_or_404()
    )
    request_data = EditionPostRequest.parse_obj(request.json)
    if request_data.build_url:
        build: Optional[Build] = build_from_url(request_data.build_url)
    else:
        build = None

    try:
        edition = create_edition(
            product=product,
            title=request_data.title,
            tracking_mode=request_data.mode,
            slug=request_data.slug,
            autoincrement_slug=request_data.autoincrement,
            tracked_ref=(
                request_data.tracked_refs[0]
                if isinstance(request_data.tracked_refs, list)
                else None
            ),
            build=build,
        )
    except Exception:
        db.session.rollback()
        raise

    task = launch_tasks()
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
    try:
        edition.deprecate()
        db.session.commit()
    except Exception:
        db.session.rollback()

    request_dashboard_build(edition.product)
    task = launch_tasks()

    response = QueuedResponse.from_task(task)
    return response.json(), 200


@api.route("/products/<slug>/editions/", methods=["GET"])
@accept_fallback
@log_route()
def get_product_editions(slug: str) -> str:
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
    default_org = Organization.query.order_by(Organization.id).first_or_404()
    editions = (
        Edition.query.join(Product, Product.id == Edition.product_id)
        .join(Organization, Organization.id == Product.organization_id)
        .filter(Organization.slug == default_org.slug)
        .filter(Product.slug == slug)
        .filter(Edition.date_ended == None)  # noqa: E711
        .all()
    )
    edition_urls = [url_for_edition(edition) for edition in editions]
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
           "title": "Development main",
           "tracked_refs": [
               "main"
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
           "title": "Development main"
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
           "title": "Development main",
           "tracked_refs": [
               "main"
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
    request_data = EditionPatchRequest.parse_obj(request.json)
    if request_data.build_url:
        build: Optional[Build] = build_from_url(request_data.build_url)
    else:
        build = None

    try:
        edition = update_edition(
            edition=edition,
            build=build,
            title=request_data.title,
            slug=request_data.slug,
            tracking_mode=request_data.mode,
            tracked_ref=(
                request_data.tracked_refs[0]
                if isinstance(request_data.tracked_refs, list)
                else None
            ),
            pending_rebuild=request_data.pending_rebuild,
        )
    except Exception:
        db.session.rollback()
        raise

    # Run the task queue
    task = launch_tasks()

    response = EditionResponse.from_edition(edition, task=task)
    return response.json()
