"""API v1 routes for products."""

from flask import jsonify, request
from . import api
from .. import db
from ..auth import token_auth
from ..models import Product


@api.route('/products/', methods=['GET'])
def get_products():
    """GET listing of all products."""
    return jsonify({'products': [product.get_url() for product in
                                 Product.query.all()]})


@api.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    """GET single product by table row id."""
    return jsonify(Product.query.get_or_404(id).export_data())


@api.route('/products/', methods=['POST'])
@token_auth.login_required
def new_product():
    """POST a new product. Token authentication required."""
    product = Product()
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({}), 201, {'Location': product.get_url()}


@api.route('/products/<int:id>', methods=['PUT'])
@token_auth.login_required
def edit_product(id):
    """PUT changes to a product. Token authentication required."""
    product = Product.query.get_or_404(id)
    product.import_data(request.json)
    db.session.add(product)
    db.session.commit()
    return jsonify({})
