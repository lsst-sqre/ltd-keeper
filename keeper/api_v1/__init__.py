from flask import Blueprint

api = Blueprint('api', __name__)

from . import products, builds, editions, dashboards, errorhandlers  # NOQA
