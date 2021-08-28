"""Test /v2/ APIs for projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

# from keeper.models import Organization, db
from keeper.testutils import MockTaskQueue

if TYPE_CHECKING:
    from unittest.mock import Mock

    from keeper.testutils import TestClient


def test_projects(client: TestClient, mocker: Mock) -> None:
    task_queue = mocker.patch(
        "keeper.taskrunner.inspect_task_queue", return_value=None
    )
    task_queue = MockTaskQueue(mocker)  # noqa

    # Create a default organization ===========================================
    mocker.resetall()

    request_data = {
        "slug": "test1",
        "title": "Test 1",
        "layout": "subdomain",
        "domain": "example.org",
        "path_prefix": "/",
        "bucket_name": "test-bucket",
        "fastly_support": True,
        "fastly_domain": "fastly.example.org",
        "fastly_service_id": "abc",
        "fastly_api_key": "123",
    }
    r = client.post("/v2/orgs", request_data)
    task_queue.apply_task_side_effects()
    assert r.status == 201
    org1_url = r.headers["Location"]
    org1_projects_url = r.json["projects_url"]

    # Get project list (should be empty) ======================================
    mocker.resetall()

    r = client.get(org1_projects_url)
    assert r.status == 200
    assert len(r.json) == 0

    # Create a project ========================================================
    mocker.resetall()

    request_data = {
        "slug": "alpha",
        "title": "Alpha",
        "source_repo_url": "https://github.com/example/alpha",
        "default_edition_mode": "git_refs",
    }
    r = client.post(org1_projects_url, request_data)
    task_queue.apply_task_side_effects()
    assert r.status == 201
    project1_url = r.headers["Location"]
    project1_data = r.json

    assert project1_data["organization_url"] == org1_url
    assert project1_data["self_url"] == project1_url
    assert project1_data["published_url"] == "https://alpha.example.org"

    # Get project list again ==================================================
    mocker.resetall()

    r = client.get(org1_projects_url)
    assert r.status == 200
    assert r.json[0] == project1_data

    # Update title ============================================================
    mocker.resetall()

    request_data = {"title": "Alpha Docs"}
    r = client.patch(project1_url, request_data)
    task_queue.apply_task_side_effects()
    assert r.status == 200
    assert r.json["title"] == "Alpha Docs"
