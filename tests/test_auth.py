"""Test /token route to get auth token from a client providing a
username+password.
"""


def test_get_token(basic_client):
    r = basic_client.get("/token")
    assert r.status == 200
    assert "token" in r.json
