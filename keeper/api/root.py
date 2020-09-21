"""Root API route (GET /)."""

from flask import jsonify, url_for
from flask_accept import accept_fallback

from keeper.api import api
from keeper.logutils import log_route
from keeper.version import get_version


@api.route("/", methods=["GET"])
@accept_fallback
@log_route()
def get_root() -> None:
    """Root API route."""
    version = get_version()
    data = {
        "server_version": version,
        "documentation": "https://ltd-keeper.lsst.io",
        "message": (
            "LTD Keeper is the API service for managing LSST the Docs "
            "projects."
        ),
    }

    links = {
        "self": url_for("api.get_root", _external=True),
        "token": url_for("api.get_auth_token", _external=True),
        "products": url_for("api.get_products", _external=True),
    }
    return jsonify({"data": data, "links": links})
