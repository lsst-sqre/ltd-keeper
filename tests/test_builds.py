"""Tests for the builds API."""

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


def test_builds(client: TestClient, mocker: Mock) -> None:
    mock_registry.patch_all(mocker)

    # Create default organization
    from keeper.models import Organization, db

    org = Organization(
        slug="test",
        title="Test",
        root_domain="lsst.io",
        fastly_domain="global.ssl.fastly.net",
        bucket_name="bucket-name",
    )
    db.session.add(org)
    db.session.commit()

    # ========================================================================
    # Add product /products/pipelines
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
    # Add a sample edition
    mocker.resetall()

    e = {
        "tracked_refs": ["master"],
        "slug": "latest",
        "title": "Latest",
        "published_url": "pipelines.lsst.io",
    }
    r = client.post(product_url + "/editions/", e)

    # Initially no builds
    r = client.get("/products/pipelines/builds/")
    assert r.status == 200
    assert len(r.json["builds"]) == 0

    # ========================================================================
    # Add a build
    mocker.resetall()

    b1 = {
        "slug": "b1",
        "github_requester": "jonathansick",
        "git_refs": ["master"],
    }
    r = client.post("/products/pipelines/builds/", b1)
    assert r.status == 201
    assert r.json["product_url"] == product_url
    assert r.json["slug"] == b1["slug"]
    assert r.json["date_created"] is not None
    assert r.json["date_ended"] is None
    assert r.json["uploaded"] is False
    assert r.json["published_url"] == "https://pipelines.lsst.io/builds/b1"
    assert len(r.json["surrogate_key"]) == 32  # should be a uuid4 -> hex
    build_url = r.headers["Location"]

    # ========================================================================
    # Re-add build with same slug; should fail
    mocker.resetall()

    with pytest.raises(ValidationError):
        r = client.post("/products/pipelines/builds/", b1)

    # ========================================================================
    # List builds
    mocker.resetall()

    r = client.get("/products/pipelines/builds/")
    assert r.status == 200
    assert len(r.json["builds"]) == 1

    # ========================================================================
    # Get build
    mocker.resetall()

    r = client.get(build_url)
    assert r.status == 200
    assert r.json["bucket_name"] == "bucket-name"
    assert r.json["bucket_root_dir"] == "pipelines/builds/b1"

    # ========================================================================
    # Register upload
    mocker.resetall()

    r = client.patch(build_url, {"uploaded": True})
    assert r.status == 200

    mock_registry["keeper.models.append_task_to_chain"].assert_any_call(
        rebuild_edition.si("http://example.test/editions/1", 1)
    )
    mock_registry["keeper.models.append_task_to_chain"].assert_any_call(
        rebuild_edition.si("http://example.test/editions/2", 2)
    )
    mock_registry["keeper.api.builds.append_task_to_chain"].assert_called_with(
        build_dashboard.si(product_url)
    )
    mock_registry["keeper.api.builds.launch_task_chain"].assert_called_once()

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e0 = client.get("http://example.test/editions/1").json
    assert e0["pending_rebuild"] is True
    r = client.patch(
        "http://example.test/editions/1", {"pending_rebuild": False}
    )
    e1 = client.get("http://example.test/editions/2").json
    assert e1["pending_rebuild"] is True
    r = client.patch(
        "http://example.test/editions/2", {"pending_rebuild": False}
    )

    r = client.get(build_url)
    assert r.json["uploaded"] is True

    # ========================================================================
    # Check that the edition was rebuilt
    mocker.resetall()

    edition_data = client.get("http://example.test/editions/2")
    assert edition_data.json["build_url"] == build_url

    # ========================================================================
    # Deprecate build
    mocker.resetall()

    r = client.delete("/builds/1")
    assert r.status == 200

    r = client.get("/builds/1")
    assert r.json["product_url"] == product_url
    assert r.json["slug"] == b1["slug"]
    assert r.json["date_created"] is not None
    assert r.json["date_ended"] is not None

    # Build no longer in listing
    r = client.get("/products/pipelines/builds/")
    assert r.status == 200
    assert len(r.json["builds"]) == 0

    # ========================================================================
    # Add an auto-slugged build
    mocker.resetall()

    b2 = {"git_refs": ["master"]}
    r = client.post("/products/pipelines/builds/", b2)

    assert r.status == 201
    assert r.json["slug"] == "1"

    mock_registry[
        "keeper.api.post_products_builds.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry[
        "keeper.api.post_products_builds.launch_task_chain"
    ].assert_called_once()

    # ========================================================================
    # Add an auto-slugged build
    mocker.resetall()

    b3 = {"git_refs": ["master"]}
    r = client.post("/products/pipelines/builds/", b3)

    assert r.status == 201
    assert r.json["slug"] == "2"

    mock_registry[
        "keeper.api.post_products_builds.append_task_to_chain"
    ].assert_called_with(build_dashboard.si(product_url))
    mock_registry[
        "keeper.api.post_products_builds.launch_task_chain"
    ].assert_called_once()

    # ========================================================================
    # Add a build missing 'git_refs'
    mocker.resetall()

    b4 = {"slug": "bad-build"}
    with pytest.raises(ValidationError):
        r = client.post("/products/pipelines/builds/", b4)

    # ========================================================================
    # Add a build with a badly formatted git_refs
    mocker.resetall()

    b5 = {"slug": "another-bad-build", "git_refs": "master"}
    with pytest.raises(ValidationError):
        r = client.post("/products/pipelines/builds/", b5)

    # ========================================================================
    # Add a build and see if an edition was automatically created
    mocker.resetall()

    b6 = {"git_refs": ["tickets/DM-1234"]}
    r = client.post("/products/pipelines/builds/", b6)
    assert r.status == 201
    r = client.get("/products/pipelines/editions/")
    assert len(r.json["editions"]) == 3
    editions = sorted(r.json["editions"])  # postgres and sqlite differ orders
    auto_edition_url = editions[-1]
    r = client.get(auto_edition_url)
    assert r.json["slug"] == "DM-1234"


# Authorizion tests: POST /products/<slug>/builds/ ===========================
# Only the build-upload auth'd client should get in


def test_post_build_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.post("/products/test/builds/", {"foo": "bar"})
    assert r.status == 401


def test_post_build_auth_product_client(product_client: TestClient) -> None:
    r = product_client.post("/products/test/builds/", {"foo": "bar"})
    assert r.status == 403


def test_post_build_auth_edition_client(edition_client: TestClient) -> None:
    r = edition_client.post("/products/test/builds/", {"foo": "bar"})
    assert r.status == 403


def test_post_build_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    with pytest.raises(NotFound):
        upload_build_client.post("/products/test/builds/", {"foo": "bar"})


def test_post_build_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    r = deprecate_build_client.post("/products/test/builds/", {"foo": "bar"})
    assert r.status == 403


# Authorizion tests: PATCH /products/<slug>/builds/ ==========================
# Only the build-upload auth'd client should get in


def test_patch_build_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.patch("/builds/1", {"foo": "bar"})
    assert r.status == 401


def test_patch_build_auth_product_client(product_client: TestClient) -> None:
    r = product_client.patch("/builds/1", {"foo": "bar"})
    assert r.status == 403


def test_patch_build_auth_edition_client(edition_client: TestClient) -> None:
    r = edition_client.patch("/builds/1", {"foo": "bar"})
    assert r.status == 403


def test_patch_build_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    with pytest.raises(NotFound):
        upload_build_client.patch("/builds/1", {"foo": "bar"})


def test_patch_build_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    r = deprecate_build_client.patch("/builds/1", {"foo": "bar"})
    assert r.status == 403


# Authorizion tests: DELETE /products/<slug>/builds/ =========================
# Only the build-deprecator auth'd client should get in


def test_delete_build_auth_anon(anon_client: TestClient) -> None:
    r = anon_client.delete("/builds/1")
    assert r.status == 401


def test_delete_build_auth_product_client(product_client: TestClient) -> None:
    r = product_client.delete("/builds/1")
    assert r.status == 403


def test_delete_build_auth_edition_client(edition_client: TestClient) -> None:
    r = edition_client.delete("/builds/1")
    assert r.status == 403


def test_delete_build_auth_builduploader_client(
    upload_build_client: TestClient,
) -> None:
    r = upload_build_client.delete("/builds/1")
    assert r.status == 403


def test_delete_build_auth_builddeprecator_client(
    deprecate_build_client: TestClient,
) -> None:
    with pytest.raises(NotFound):
        deprecate_build_client.delete("/builds/1", {"foo": "bar"})
