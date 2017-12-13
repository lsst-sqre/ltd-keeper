"""Error handling functions.

Flask calls these functions when different HTTP error codes or Python
exceptions are emitted. These handlers provide a JSON response rather
than the default HMTL header response.
"""

from flask import jsonify
import structlog

from ..exceptions import ValidationError
from . import api


@api.errorhandler(ValidationError)
def bad_request(e):
    """Handler for ValidationError exceptions."""
    response = jsonify({'status': 400, 'error': 'bad request',
                        'message': e.args[0]})
    response.status_code = 400
    return response


@api.app_errorhandler(404)
def not_found(e):
    """App-wide handler for HTTP 404 errors."""
    response = jsonify({'status': 404, 'error': 'not found',
                        'message': 'invalid resource URI'})
    response.status_code = 404
    return response


@api.errorhandler(405)
def method_not_supported(e):
    """Handler for HTTP 405 exceptions."""
    response = jsonify({'status': 405, 'error': 'method not supported',
                        'message': 'the method is not supported'})
    response.status_code = 405
    return response


@api.app_errorhandler(500)
def internal_server_error(e):
    """App-wide handler for HTTP 500 errors."""
    logger = structlog.get_logger()
    logger.error(status=500, message=e.args[0])

    response = jsonify({'status': 500, 'error': 'internal server error',
                        'message': e.args[0]})
    response.status_code = 500
    return response
