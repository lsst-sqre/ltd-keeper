from flask import Blueprint

api = Blueprint('api', __name__)

from . import (root, products, builds, editions, dashboards, queue,
               errorhandlers, auth)
