"""API v1 route for dashboard building."""

from flask import jsonify
from . import api
from ..auth import token_auth, permission_required
from ..models import Product, Permission
from ..taskrunner import launch_task_chain, append_task_to_chain
from ..tasks.dashboardbuild import build_dashboard


@api.route('/dashboards', methods=['POST'])
@token_auth.login_required
@permission_required(Permission.ADMIN_PRODUCT)
def rebuild_all_dashboards():
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
        append_task_to_chain(build_dashboard.si(product.get_url()))
    launch_task_chain()
    return jsonify({}), 202, {}
