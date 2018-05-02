"""API resources for the celery task queue.
"""

from flask import jsonify, abort, url_for
from ..celery import celery_app

from . import api
from ..logutils import log_route


@api.route('/queue/<id>', methods=['GET'])
@log_route()
def get_task_status(id):
    try:
        task = celery_app.AsyncResult(id)
    except Exception:
        abort(404)

    data = {
        'id': id,
        'self_url': url_for('api.get_task_status', id=id, _external=True),
        'status': task.state,
        'metadata': task.info
    }

    return jsonify(data), 200, {'Location': data['self_url']}
