"""Utilties for unit testing.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""


from base64 import b64encode
from collections import namedtuple
import json
from urllib.parse import urlsplit, urlunsplit

response = namedtuple('response', 'status headers json')


class TestClient():
    """TestClient wraps Flask's/Werkzeug's built-in testing client.

    The `get`, `post`, `put`, `delete` methods mirror HTTP
    commands and return a `response` `namedtuple` with fields:

    - `status`: the integer HTTP response code
    - `header`: the HTTP response headers
    - `json`: the return data, parse as JSON into a Python `dict` object.
    """
    def __init__(self, app, username, password=''):
        self.app = app
        self.auth = 'Basic ' + b64encode((username + ':' + password)
                                         .encode('utf-8')).decode('utf-8')

    def send(self, url, method='GET', data=None, headers=None):
        # for testing, URLs just need to have the path and query string
        url_parsed = urlsplit(url)
        url = urlunsplit(('', '', url_parsed.path, url_parsed.query,
                          url_parsed.fragment))

        # Append the authentication headers to all requests
        default_headers = {
            'Authorization': self.auth,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if headers is not None:
            default_headers.update(headers)
            headers = default_headers
        else:
            headers = default_headers

        # convert JSON data to a string
        if data:
            data = json.dumps(data)

        # send request to the test client and return the response
        with self.app.test_request_context(url, method=method, data=data,
                                           headers=headers):
            rv = self.app.preprocess_request()
            if rv is None:
                rv = self.app.dispatch_request()
            rv = self.app.make_response(rv)
            rv = self.app.process_response(rv)
            return response(rv.status_code, rv.headers,
                            json.loads(rv.data.decode('utf-8')))

    def get(self, url, headers=None):
        return self.send(url, 'GET', headers=headers)

    def post(self, url, data, headers=None):
        return self.send(url, 'POST', data, headers=headers)

    def put(self, url, data, headers=None):
        return self.send(url, 'PUT', data, headers=headers)

    def patch(self, url, data, headers=None):
        return self.send(url, 'PATCH', data, headers=headers)

    def delete(self, url, headers=None):
        return self.send(url, 'DELETE', headers=headers)
