"""API resources for the celery task queue."""

from typing import Dict, Tuple

from flask import abort, jsonify, url_for
from flask_accept import accept_fallback

from keeper.api import api
from keeper.celery import celery_app
from keeper.logutils import log_route


@api.route("/queue/<id>", methods=["GET"])
@accept_fallback
@log_route()
def get_task_status(id: int) -> Tuple[str, int, Dict[str, str]]:
    try:
        if celery_app is not None:
            task = celery_app.AsyncResult(id)
        else:
            abort(500)
    except Exception:
        abort(404)

    data = {
        "id": id,
        "self_url": url_for("api.get_task_status", id=id, _external=True),
        "status": task.state,
        "metadata": task.info,
    }

    return jsonify(data), 200, {"Location": data["self_url"]}
