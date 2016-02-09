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
        return jsonify({'token': g.user.generate_auth_token()})

    return app
