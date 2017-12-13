"""Root API route (GET /).
"""

from flask import jsonify, url_for
from . import api
from ..version import get_version


@api.route('/', methods=['GET'])
def get_root():
    """Root API route.
    """
    version = get_version()
    data = {
        'server_version': version,
        'documentation': 'https://ltd-keeper.lsst.io',
        'message': ('LTD Keeper is the API service for managing LSST the Docs '
                    'projects.')
    }

    links = {
        'self': url_for('api.get_root', _external=True),
        'token': url_for('get_auth_token', _external=True),
        'products': url_for('api.get_products', _external=True),
    }
    return jsonify({
        'data': data,
        'links': links
    })
