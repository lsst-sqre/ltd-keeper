import os
from flask import Flask, jsonify, g
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name):
    """Create an application instance.

    This is called by a runner script, such as /run.py.
    """
    from .auth import password_auth

    app = Flask(__name__)

    # apply configuration
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(_this_dir, '../config', config_name + '.py')
    app.config.from_pyfile(cfg)

    # initialize extensions
    db.init_app(app)

    # register blueprints
    from .api_v1 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/v1')

    # authentication token route
    @app.route('/token')
    @password_auth.login_required
    def get_auth_token():
        """Obtain a token for API users.

        **Example request**

        .. code-block:: http

           GET /token HTTP/1.1
           Accept: */*
           Accept-Encoding: gzip, deflate
           Authorization: Basic dXNlcjpwYXNz
           Connection: keep-alive
           Host: localhost:5000
           User-Agent: HTTPie/0.9.3

        **Example response**

        .. code-block:: http

           HTTP/1.0 200 OK
           Content-Length: 139
           Content-Type: application/json
           Date: Tue, 09 Feb 2016 20:23:11 GMT
           Server: Werkzeug/0.11.3 Python/3.5.0

           {
               "token": "eyJhbGciOiJIUzI1NiIsImlhdCI6MTQ1NTA0OTM5MSwiZXhwIjoxNDU1MDUyOTkxfQ.eyJpZCI6MX0.rnAI6_aJp4DtKLiJ7qkfW-luUMUNsps-ZBZFAaIBsZQ"
           }

        :reqheader Authorization: ``username:password``
        :>json string token: Token string. Use this token in the basic auth
           ``username`` field.
        """
        return jsonify({'token': g.user.generate_auth_token()})

    return app
