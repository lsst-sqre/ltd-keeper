"""API v1 route for dashboard building."""

from __future__ import annotations

from typing import Dict, Tuple

from flask_accept import accept_fallback

from keeper.api import api
from keeper.auth import permission_required, token_auth
from keeper.models import Permission, Product
from keeper.services.requestdashboardbuild import request_dashboard_build
from keeper.taskrunner import launch_tasks

from ._models import QueuedResponse


@api.route("/dashboards", methods=["POST"])
@accept_fallback
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def rebuild_all_dashboards() -> Tuple[str, int, Dict[str, str]]:
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
        request_dashboard_build(product)
    task = launch_tasks()
    response = QueuedResponse.from_task(task)
    return response.json(), 202, {}
