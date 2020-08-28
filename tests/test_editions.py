"""Tests APIs related to edition resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from werkzeug.exceptions import NotFound

from keeper.exceptions import ValidationError
from keeper.taskrunner import mock_registry
from keeper.tasks.dashboardbuild import build_dashboard
from keeper.tasks.editionrebuild import rebuild_edition

if TYPE_CHECKING:
    from unittest.mock import Mock

    from keeper.testutils import TestClient


def test_editions(client: TestClient, mocker: Mock) -> None:
    """Exercise different /edition/ API scenarios.
    """
    mock_registry.patch_all(mocker)

    # ========================================================================
    # Add product /products/ldm-151
    mocker.resetall()

    p = {
        "slug": "pipelines",
        "doc_repo": "https://github.com/lsst/pipelines_docs.git",
        "title": "LSST Science Pipelines",
        "root_domain": "lsst.io",
        "root_fastly_domain": "global.ssl.fastly.net",
        "bucket_name": "bucket-name",
    }
    r = client.post("/products/", p)
    product_url = r.headers["Location"]

    assert r.status == 201
    mock_registry[
        "keeper.api.products.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry["keeper.api.products.launch_task_chain"].assert_called_once()

    # ========================================================================
    # Get default edition
    mocker.resetall()

    edition_urls = client.get("/products/pipelines/editions/").json
    e0_url = edition_urls["editions"][0]
    e0 = client.get(e0_url).json
    assert e0["pending_rebuild"] is False

    # ========================================================================
    # Create a build of the 'master' branch
    mocker.resetall()

    r = client.post("/products/pipelines/builds/", {"git_refs": ["master"]})
    b1_url = r.json["self_url"]
    assert r.status == 201

    # ========================================================================
    # Confirm build of the 'master' branch
    mocker.resetall()

    client.patch(b1_url, {"uploaded": True})

    mock_registry["keeper.models.append_task_to_chain"].assert_called_with(
        rebuild_edition.si("http://example.test/editions/1", 1)
    )
    mock_registry["keeper.api.builds.append_task_to_chain"].assert_called_with(
        build_dashboard.si(product_url)
    )
    mock_registry["keeper.api.builds.launch_task_chain"].assert_called_once()

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e0 = client.get(e0_url).json
    assert e0["pending_rebuild"] is True
    r = client.patch(e0_url, {"pending_rebuild": False})

    # ========================================================================
    # Create a second build of the 'master' branch
    mocker.resetall()

    r = client.post("/products/pipelines/builds/", {"git_refs": ["master"]})
    assert r.status == 201
    b2_url = r.json["self_url"]

    # ========================================================================
    # Confirm second build of the 'master' branch
    mocker.resetall()

    client.patch(b2_url, {"uploaded": True})

    mock_registry["keeper.models.append_task_to_chain"].assert_called_with(
        rebuild_edition.si("http://example.test/editions/1", 1)
    )
    mock_registry["keeper.api.builds.append_task_to_chain"].assert_called_with(
        build_dashboard.si(product_url)
    )
    mock_registry["keeper.api.builds.launch_task_chain"].assert_called_once()

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e0 = client.get(e0_url).json
    assert e0["pending_rebuild"] is True
    r = client.patch(e0_url, {"pending_rebuild": False})

    # ========================================================================
    # Setup an edition also tracking master called 'latest'
    mocker.resetall()

    e1 = {
        "tracked_refs": ["master"],
        "slug": "latest",
        "title": "Latest",
        "build_url": b1_url,
    }
    r = client.post(product_url + "/editions/", e1)
    e1_url = r.headers["Location"]

    r = client.get(e1_url)
    assert r.status == 200
    assert r.json["tracked_refs"][0] == e1["tracked_refs"][0]
    assert r.json["slug"] == e1["slug"]
    assert r.json["title"] == e1["title"]
    assert r.json["build_url"] == b1_url
    assert r.json["date_created"] is not None
    assert r.json["date_ended"] is None
    assert r.json["published_url"] == "https://pipelines.lsst.io/v/latest"
    assert r.json["pending_rebuild"] is True

    mock_registry[
        "keeper.api.editions.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry["keeper.models.append_task_to_chain"].assert_called_with(
        rebuild_edition.si(e1_url, 2)
    )
    mock_registry["keeper.api.editions.launch_task_chain"].assert_called_once()

    # Manually reset pending_rebuild since the rebuild_edition task is mocked
    r = client.patch(e1_url, {"pending_rebuild": False})

    # ========================================================================
    # Re-build the edition with the second build
    mocker.resetall()

    r = client.patch(e1_url, {"build_url": b2_url})

    assert r.status == 200
    assert r.json["build_url"] == b2_url

    mock_registry["keeper.models.append_task_to_chain"].assert_called_with(
        rebuild_edition.si(e1_url, 2)
    )
    mock_registry[
        "keeper.api.editions.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry["keeper.api.editions.launch_task_chain"].assert_called_once()

    # Manually reset pending_rebuild since the rebuild_edition task is mocked
    r = client.patch(e1_url, {"pending_rebuild": False})

    # ========================================================================
    # Change the title with PATCH
    mocker.resetall()

    r = client.patch(e1_url, {"title": "Development version"})
    assert r.status == 200
    assert r.json["title"] == "Development version"
    assert r.json["pending_rebuild"] is False

    mock_registry[
        "keeper.api.editions.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry["keeper.api.editions.launch_task_chain"].assert_called_once()

    # ========================================================================
    # Change the tracked_refs with PATCH
    mocker.resetall()

    r = client.patch(e1_url, {"tracked_refs": ["tickets/DM-9999", "master"]})

    assert r.status == 200
    assert r.json["tracked_refs"][0] == "tickets/DM-9999"
    assert r.json["tracked_refs"][1] == "master"
    assert r.json["pending_rebuild"] is False  # no need to rebuild

    mock_registry[
        "keeper.api.editions.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry["keeper.api.editions.launch_task_chain"].assert_called_once()

    # ========================================================================
    # Deprecate the editon
    mocker.resetall()

    r = client.delete(e1_url)
    assert r.status == 200

    r = client.get(e1_url)
    assert r.status == 200
    assert r.json["date_ended"] is not None

    # Deprecated editions no longer in the editions list
    r = client.get(product_url + "/editions/")
    assert r.status == 200
    # only default edition (main) remains
    assert len(r.json["editions"]) == 1

    # ========================================================================
    # Verify we can't make a second 'main' edition
    mocker.resetall()

    with pytest.raises(ValidationError):
        r = client.post(
            "/products/pipelines/editions/",
            {"slug": "main", "tracked_refs": ["master"], "title": "Main"},
        )


# Authorizion tests: POST /products/<slug>/editions/ =========================
# Only the full admin client and the edition-authorized client should get in


def test_post_edition_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.post("/products/test/editions/", {"foo": "bar"})
    assert r.status == 401


def test_post_edition_auth_product_client(product_client: TestClient) -> None:
    r = product_client.post("/products/test/editions/", {"foo": "bar"})
    assert r.status == 403


def test_post_edition_auth_edition_client(edition_client: TestClient) -> None:
    with pytest.raises(NotFound):
        edition_client.post("/products/test/editions/", {"foo": "bar"})


def test_post_edition_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    r = upload_build_client.post("/products/test/editions/", {"foo": "bar"})
    assert r.status == 403


def test_post_edition_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    r = deprecate_build_client.post("/products/test/editions/", {"foo": "bar"})
    assert r.status == 403


# Authorizion tests: PATCH /editions/<slug>/editions/ =========================
# Only the full admin client and the edition-authorized client should get in


def test_patch_edition_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.patch("/editions/1", {"foo": "bar"})
    assert r.status == 401


def test_patch_edition_auth_product_client(product_client: TestClient) -> None:
    r = product_client.patch("/editions/1", {"foo": "bar"})
    assert r.status == 403


def test_patch_edition_auth_edition_client(edition_client: TestClient) -> None:
    with pytest.raises(NotFound):
        edition_client.patch("/editions/1", {"foo": "bar"})


def test_patch_edition_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    r = upload_build_client.patch("/editions/1", {"foo": "bar"})
    assert r.status == 403


def test_patch_edition_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    r = deprecate_build_client.patch("/editions/1", {"foo": "bar"})
    assert r.status == 403


# Authorizion tests: DELETE /editions/<slug> =================================
# Only the full admin client and the edition-authorized client should get in


def test_delete_edition_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.delete("/editions/1")
    assert r.status == 401


def test_delete_edition_auth_product_client(
    product_client: TestClient,
) -> None:
    r = product_client.delete("/editions/1")
    assert r.status == 403


def test_delete_edition_auth_edition_client(
    edition_client: TestClient,
) -> None:
    with pytest.raises(NotFound):
        edition_client.delete("/editions/1")


def test_delete_edition_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    r = upload_build_client.delete("/editions/1")
    assert r.status == 403


def test_delete_edition_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    r = deprecate_build_client.delete("/editions/1")
    assert r.status == 403
