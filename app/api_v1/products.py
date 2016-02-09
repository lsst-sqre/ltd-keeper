"""API v1 routes for products."""

from flask import jsonify, request
from . import api
from .. import db
from ..auth import token_auth
from ..models import Product


@api.route('/products/', methods=['GET'])
def get_products():
    """List all documentation products (anonymous access allowed).

    **Example request**

    .. code-block:: http

        GET /v1/products/ HTTP/1.1

    **Example response**

    .. code-block:: http

        HTTP/1.0 200 OK

    :reqheader Authorization: ``<token>:``
    """
    return jsonify({'products': [product.get_url() for product in
                                 Product.query.all()]})


@api.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    """Get the record of a single documentation product (anonymous access
    allowed).
    """
    return jsonify(Product.query.get_or_404(id).export_data())


@api.route('/products/', methods=['POST'])
@token_auth.login_required
def new_product():
    """Create a new documentation product (token required)."""
    product = Product()
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({}), 201, {'Location': product.get_url()}


@api.route('/products/<int:id>', methods=['PUT'])
@token_auth.login_required
def edit_product(id):
    """Update a product (token required)."""
    product = Product.query.get_or_404(id)
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({})
