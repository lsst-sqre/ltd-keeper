"""Root API route (GET /)."""

from flask import current_app, url_for
from flask_accept import accept_fallback

from keeper.apiroot import apiroot
from keeper.logutils import log_route
from keeper.version import get_version

from ._models import RootData, RootLinks, RootResponse


@apiroot.route("/", methods=["GET"])
@accept_fallback
@log_route()
def get_root() -> str:
    """Root API route."""
    version = get_version()
    root_data = RootData(
        server_version=version,
        documentation="https://ltd-keeper.lsst.io",
        message=(
            "LTD Keeper is the API service for managing LSST the Docs "
            "projects."
        ),
    )
    links = RootLinks(
        self_url=url_for("apiroot.get_root", _external=True),
        token=url_for("apiroot.get_auth_token", _external=True),
        products=(
            url_for("api.get_products", _external=True)
            if current_app.config["ENABLE_V1_API"]
            else None
        ),
    )
    response = RootResponse(data=root_data, links=links)
    return response.json(by_alias=True)
