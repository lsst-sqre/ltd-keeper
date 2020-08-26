"""Test making editions where their slug is a monotonically increasing integer,
using the autoincrement=True feature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.taskrunner import mock_registry

if TYPE_CHECKING:
    from unittest.mock import Mock

    from keeper.testutils import TestClient


def test_editions_autoincrement(client: TestClient, mocker: Mock) -> None:
    """Test creating editions with autoincrement=True.
    """
    mock_registry.patch_all(mocker)

    # ========================================================================
    # Add product /products/testr-000
    mocker.resetall()

    p = {
        "slug": "testr-000",
        "doc_repo": "https://github.com/lsst/TESTR-000",
        "title": "Demo test report",
        "root_domain": "lsst.io",
        "root_fastly_domain": "global.ssl.fastly.net",
        "bucket_name": "bucket-name",
        "main_mode": "manual",
    }
    r = client.post("/products/", p)
    product_url = r.headers["Location"]

    # ========================================================================
    # Get default edition
    # mocker.resetall()

    # edition_urls = client.get('/products/pipelines/editions/').json
    # e0_url = edition_urls['editions'][0]

    # ========================================================================
    # Create first autoincremented edition
    mocker.resetall()

    response = client.post(
        product_url + "/editions/",
        {"autoincrement": "True", "mode": "manual"},
    )
    assert response.status == 201
    e1_url = response.headers["Location"]

    # ========================================================================
    # Get first autoincremented edition
    mocker.resetall()

    response = client.get(e1_url)
    assert response.status == 200
    assert response.json["self_url"] == e1_url
    assert response.json["slug"] == "1"
    assert response.json["title"] == "1"
    assert response.json["mode"] == "manual"

    # ========================================================================
    # Create second autoincremented edition
    mocker.resetall()

    response = client.post(
        product_url + "/editions/",
        {"autoincrement": "True", "mode": "manual"},
    )
    assert response.status == 201
    e2_url = response.headers["Location"]

    # ========================================================================
    # Get second autoincremented edition
    mocker.resetall()

    response = client.get(e2_url)
    assert response.status == 200
    assert response.json["self_url"] == e2_url
    assert response.json["slug"] == "2"
    assert response.json["title"] == "2"
    assert response.json["mode"] == "manual"

    # ========================================================================
    # Create a regular (git_ref tracking) edition
    mocker.resetall()

    response = client.post(
        product_url + "/editions/",
        {"tracked_refs": ["v1.0"], "slug": "v1.0", "title": "v1.0"},
    )
    assert response.status == 201
    e3_url = response.headers["Location"]

    # ========================================================================
    # Get that v1.0 edition
    mocker.resetall()

    response = client.get(e3_url)
    assert response.status == 200
    assert response.json["self_url"] == e3_url
    assert response.json["slug"] == "v1.0"
    assert response.json["title"] == "v1.0"
    assert response.json["mode"] == "git_refs"

    # ========================================================================
    # Create third autoincremented edition
    mocker.resetall()

    response = client.post(
        product_url + "/editions/",
        {"autoincrement": "True", "mode": "manual"},
    )
    assert response.status == 201
    e4_url = response.headers["Location"]

    # ========================================================================
    # Get third autoincremented edition
    mocker.resetall()

    response = client.get(e4_url)
    assert response.status == 200
    assert response.json["self_url"] == e4_url
    assert response.json["slug"] == "3"
    assert response.json["title"] == "3"
    assert response.json["mode"] == "manual"
