"""API v1 routes for versions."""

from datetime import datetime
from flask import jsonify, request

from . import api
from .. import db
from ..auth import token_auth
from ..models import Product, Build, Version


@api.route('products/<int:id>/versions/', methods=['POST'])
@token_auth.login_required
def new_version(id):
    """POST a new documentation version. Provisions the version."""
    product = Product.query.get_or_404(id)
    version = Version(product=product)
    version.import_data(request.json)
    db.session.add(version)
    db.session.commit()
    return jsonify({}), 201, {'Location': version.get_url()}


@api.route('/versions/<int:id>', methods=['DELETE'])
@token_auth.login_required
def deprecate_version(id):
    """POST to mark a version as deprecated."""
    version = Version.query.get_or_404(id)
    version.end_date = datetime.now()
    db.session.commit()
    return jsonify({}), 202


@api.route('/products/<int:id>/versions/', methods=['GET'])
def get_product_versions(id):
    """GET listing of all versions for a product."""
    version_urls = [version.get_url() for version in
                    Version.query.filter(Version.product_id == id).all()]
    return jsonify({'versions': version_urls})


@api.route('/versions/<int:id>', methods=['GET'])
def get_version(id):
    """GET a single version."""
    return jsonify(Version.query.get_or_404(id).export_data())


@api.route('/versions/<int:id>', methods=['PUT'])
def edit_version(id):
    """PUT a version (change metadata)."""
    version = Version.query.get_or_404(id)
    version.import_data(request.json)
    db.session.add(version)
    db.session.commit()
    return jsonify({})
