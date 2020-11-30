"""API v1 endpoint for getting metadata for a product dashboard."""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify
from flask_accept import accept_fallback

from keeper.api import api
from keeper.logutils import log_route
from keeper.models import Product


@api.route("/products/<slug>/dashboard", methods=["GET"])
@accept_fallback
@log_route()
def get_dashboard_metadata(slug: str) -> str:
    """Get metadata required to generate a dashboard."""
    payload: Dict[str, Any] = {}

    product = Product.query.filter_by(slug=slug).first_or_404()
    payload["product"] = product.export_data()

    payload["editions"] = []
    for edition in product.editions:
        payload["editions"].append(edition.export_data())

    payload["builds"] = []
    for build in product.builds:
        payload["builds"].append(build.export_data())

    return jsonify(payload)
