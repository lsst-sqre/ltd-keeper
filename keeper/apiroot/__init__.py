from flask import Blueprint

apiroot = Blueprint("apiroot", __name__)

from . import auth, root
