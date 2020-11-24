from flask import Blueprint

api = Blueprint("api", __name__)

from . import (
    auth,
    builds,
    dashboards,
    editions,
    errorhandlers,
    get_products_dashboard,
    post_products_builds,
    products,
    queue,
    root,
)
