"""Tests for the dashboard API."""


def test_rebuild_dashboards(client):
    """Test dashboard rebuilds with full client."""
    r = client.post("/dashboards", {})
    assert r.status == 202


def test_rebuild_dashboards_anon(anon_client):
    """Test dashaboard rebuild with anonymous client."""
    r = anon_client.post("/dashboards", {})
    assert r.status == 401


def test_rebuild_dashboards_edition(edition_client):
    """Test dashaboard rebuild with edition client."""
    r = edition_client.post("/dashboards", {})
    assert r.status == 403


def test_rebuild_dashboards_upload_build(upload_build_client):
    """Test dashaboard rebuild with upload_build client."""
    r = upload_build_client.post("/dashboards", {})
    assert r.status == 403
