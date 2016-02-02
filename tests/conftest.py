"""py.test fixtures available to all test modules without explicit import."""

import pytest

from app import create_app, db
from app.models import User
from app.testutils import TestClient


DEFAULT_USERNAME = 'hipster'
DEFAULT_PASSWORD = 'pug'


@pytest.fixture
def empty_app(request):
    """An application with only a single user, but otherwise empty"""
    app = create_app('testing')
    ctx = app.app_context()
    ctx.push()
    db.drop_all()
    db.create_all()
    u = User(username=DEFAULT_USERNAME)
    u.set_password(DEFAULT_PASSWORD)
    db.session.add(u)
    db.session.commit()

    def fin():
        db.session.remove()
        db.drop_all()
        ctx.pop()

    request.addfinalizer(fin)
    return app


@pytest.fixture
def basic_client(empty_app):
    """Client with username/password auth, using the `app` application."""
    client = TestClient(empty_app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    return client


@pytest.fixture
def client(empty_app):
    """Client with token-based auth, using the `app` application."""
    _c = TestClient(empty_app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    r = _c.get('/token')
    client = TestClient(empty_app, r.json['token'])
    return client
