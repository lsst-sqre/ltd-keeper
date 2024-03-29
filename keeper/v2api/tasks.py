"""v2 APIs related to background tasks."""

from __future__ import annotations

from typing import Dict, Tuple

from flask import Response, abort, jsonify
from flask_accept import accept_fallback

from keeper.auth import token_auth
from keeper.celery import celery_app
from keeper.logutils import log_route
from keeper.v2api import v2api

from ._urls import url_for_task


@v2api.route("/task/<id>", methods=["GET"])
@accept_fallback
@log_route()
@token_auth.login_required
def get_task(id: int) -> Tuple[Response, int, Dict[str, str]]:
    try:
        if celery_app is not None:
            task = celery_app.AsyncResult(id)
        else:
            abort(500)
    except Exception:
        abort(404)

    data = {
        "id": id,
        "self_url": url_for_task(id),
        "status": task.state,
        "metadata": task.info,
    }

    return jsonify(data), 200, {"Location": data["self_url"]}
