"""API v1 routes for builds."""

from datetime import datetime
from flask import jsonify, request

from . import api
from .. import db
from ..auth import token_auth
from ..models import Product, Build


@api.route('/products/<int:id>/builds/', methods=['POST'])
@token_auth.login_required
def new_build(id):
    """POST a new documentation build for a product."""
    product = Product.query.get_or_404(id)
    build = Build(product=product)
    build.import_data(request.json)
    db.session.add(build)
    db.session.commit()
    return jsonify({}), 201, {'Location': build.get_url()}


@api.route('/builds/<int:id>/deprecate', methods=['POST'])
@token_auth.login_required
def deprecate_build(id):
    """POST to mark a build as deprecated."""
    build = Build.query.get_or_404(id)
    build.end_date = datetime.now()
    db.session.commit()
    return jsonify({}), 202


@api.route('/products/<int:id>/builds/', methods=['GET'])
def get_product_builds(id):
    """GET listing of all builds for a product."""
    print(id)
    build_urls = [build.get_url() for build in
                  Build.query.filter(Build.product_id == id).all()]
    return jsonify({'builds': build_urls})


@api.route('/builds/<int:id>', methods=['GET'])
def get_build(id):
    """GET a single build."""
    return jsonify(Build.query.get_or_404(id).export_data())
