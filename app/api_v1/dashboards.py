"""API v1 route for dashboard building."""

from flask import jsonify, current_app
from . import api
from ..auth import token_auth, permission_required
from ..models import Product, Permission
from ..dasher import build_dashboards


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
    build_dashboards(
        [product.get_url() for product in Product.query.all()],
        current_app.config['LTD_DASHER_URL'],
        current_app.logger)
    return jsonify({}), 202, {}
