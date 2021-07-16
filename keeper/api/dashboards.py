"""API v1 route for dashboard building."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple

from flask import jsonify
from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.models import Permission, Product
from keeper.taskrunner import (
    append_task_to_chain,
    insert_task_url_in_response,
    launch_task_chain,
    mock_registry,
)
from keeper.tasks.dashboardbuild import build_dashboard

from ._urls import url_for_product

if TYPE_CHECKING:
    from flask import Response

# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.api.dashboards.launch_task_chain",
        "keeper.api.dashboards.append_task_to_chain",
    ]
)


@api.route("/dashboards", methods=["POST"])
@accept_fallback
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def rebuild_all_dashboards() -> Tuple[Response, int, Dict[str, str]]:
    """Rebuild the LTD Dasher dashboards for all products.

    Note that dashboards are built asynchronously.

    **Authorization**

    User must be authenticated and have ``admin_product`` permissions.

    :statuscode 202: Dashboard rebuild trigger sent.

    **See also**

    - :http:post:`/products/(slug)/dashboard` for single-product dashboard
      rebuilds.
    """
    for product in Product.query.all():
        product_url = url_for_product(product)
        append_task_to_chain(build_dashboard.si(product_url))
    task = launch_task_chain()
    response = insert_task_url_in_response({}, task)
    return jsonify(response), 202, {}
