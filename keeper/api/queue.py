"""API resources for the celery task queue.
"""

from flask import abort, jsonify, url_for
from flask_accept import accept_fallback

from ..celery import celery_app
from ..logutils import log_route
from . import api


@api.route("/queue/<id>", methods=["GET"])
@accept_fallback
@log_route()
def get_task_status(id):
    try:
        task = celery_app.AsyncResult(id)
    except Exception:
        abort(404)

    data = {
        "id": id,
        "self_url": url_for("api.get_task_status", id=id, _external=True),
        "status": task.state,
        "metadata": task.info,
    }

    return jsonify(data), 200, {"Location": data["self_url"]}
