"""Tests for PATCHing an edition to change the tracking mode from
``git_refs`` to ``lsst_doc``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.taskrunner import mock_registry

# from keeper.tasks.dashboardbuild import build_dashboard

if TYPE_CHECKING:
    from unittest.mock import Mock

    from keeper.testutils import TestClient


def test_pach_lsst_doc_edition(client: TestClient, mocker: Mock) -> None:
    """Test patching an edition from tracking a Git ref to an LSST doc.

    1. Create a product with the default GIT_REF tracking mode for the
       main edition.
    2. Post a build on `master`; it is tracked.
    3. Post a `v1.0` build; it is not tracked.
    4. Patch the main edition to use the LSST_DOC tracking mode.
    5. Post a `v1.1` build that is tracked.
    """
    # Mock all celergy-based tasks.
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
    # Add product /products/ldm-151
    mocker.resetall()

    p1_data = {
        "slug": "ldm-151",
        "doc_repo": "https://github.com/lsst/LDM-151",
        "main_mode": "git_refs",  # default
        "title": "Applications Design",
        "root_domain": "lsst.io",
        "root_fastly_domain": "global.ssl.fastly.net",
        "bucket_name": "bucket-name",
    }
    r = client.post("/products/", p1_data)
    product_url = r.headers["Location"]

    assert r.status == 201

    # FIXME
    # mock_registry[
    #     "keeper.services.createproduct.append_task_to_chain"
    # ].assert_called_with(build_dashboard.si(product_url))
    # mock_registry["keeper.api.products.launch_task_chain"].assert_called_once()

    # ========================================================================
    # Create a build on 'master'
    mocker.resetall()

    # Get the URL for the default edition
    r = client.get(product_url + "/editions/")
    e1_url = r.json["editions"][0]

    b1_data = {
        "slug": "b1",
        "github_requester": "jonathansick",
        "git_refs": ["master"],
    }
    r = client.post(product_url + "/builds/", b1_data)
    b1_url = r.headers["Location"]

    # ========================================================================
    # Create a build on 'master'
    mocker.resetall()

    r = client.patch(b1_url, {"uploaded": True})

    # Test that the main edition updated.
    r = client.get(e1_url)

    assert r.json["build_url"] == b1_url

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e1 = client.get(e1_url).json
    assert e1["pending_rebuild"] is True
    r = client.patch(e1_url, {"pending_rebuild": False})

    # ========================================================================
    # Create a build with a semantic version tag ('v1.0')
    mocker.resetall()

    b2_data = {
        "slug": "b2",
        "github_requester": "jonathansick",
        "git_refs": ["v1.0"],
    }
    r = client.post("/products/ldm-151/builds/", b2_data)
    b2_url = r.headers["Location"]

    # Get the URL for the new edition tracking v1-0
    r = client.get(product_url + "/editions/")
    e2_url = sorted(r.json["editions"])[1]  # postgres and sqlite orders differ

    # ========================================================================
    # Confirm upload of 'v1.0'
    mocker.resetall()

    r = client.patch(b2_url, {"uploaded": True})

    # Test that the main edition *did not* update
    r = client.get(e1_url)
    assert r.json["build_url"] == b1_url

    # FIXME
    # mock_registry["keeper.models.append_task_to_chain"].assert_called_with(
    #     rebuild_edition.si(e2_url, 2)
    # )
    # mock_registry[
    #     "keeper.services.updatebuild.append_task_to_chain"
    # ].assert_called_with(build_dashboard.si(product_url))
    # mock_registry["keeper.api.builds.launch_task_chain"].assert_called_once()

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e2 = client.get(e2_url).json
    assert e2["pending_rebuild"] is True
    r = client.patch(e2_url, {"pending_rebuild": False})

    # ========================================================================
    # PATCH the tracking mode of the edition to use `lsst_doc`
    mocker.resetall()

    edition_patch_data = {"mode": "lsst_doc"}
    r = client.patch(e1_url, edition_patch_data)
    assert r.status == 200

    e2 = client.get(e2_url).json
    assert e2["pending_rebuild"] is False

    # ========================================================================
    # Create another build with a semantic version tag: v1.1
    mocker.resetall()

    b3_data = {
        "slug": "b3",
        "github_requester": "jonathansick",
        "git_refs": ["v1.1"],
    }
    r = client.post("/products/ldm-151/builds/", b3_data)
    b3_url = r.headers["Location"]

    # Get the URL for the new edition tracking v1-1
    r = client.get(product_url + "/editions/")
    e3_url = sorted(r.json["editions"])[2]  # postgres and sqlite orders differ

    # ========================================================================
    # Confirm upload of b3
    mocker.resetall()

    r = client.patch(b3_url, {"uploaded": True})

    # Test that the main edition *did* update now
    r = client.get(e1_url)
    assert r.json["build_url"] == b3_url

    # FIXME
    # mock_registry["keeper.models.append_task_to_chain"].assert_any_call(
    #     rebuild_edition.si(e1_url, 1)
    # )
    # mock_registry["keeper.models.append_task_to_chain"].assert_any_call(
    #     rebuild_edition.si(e3_url, 3)
    # )
    # mock_registry[
    #     "keeper.services.updatebuild.append_task_to_chain"
    # ].assert_called_with(build_dashboard.si(product_url))
    # mock_registry["keeper.api.builds.launch_task_chain"].assert_called_once()

    # Check pending_rebuild semaphore and manually reset it since the celery
    # task is mocked.
    e3 = client.get(e3_url).json
    assert e3["pending_rebuild"] is True
    r = client.patch(e3_url, {"pending_rebuild": False})

    e1 = client.get(e1_url).json
    assert e1["pending_rebuild"] is True
    r = client.patch(e1_url, {"pending_rebuild": False})
