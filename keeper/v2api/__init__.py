from flask import Blueprint

v2api = Blueprint("v2api", __name__)

from . import organizations, projects, tasks
