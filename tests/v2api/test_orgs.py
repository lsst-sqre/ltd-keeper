"""Test /v2/ APIs for managing organizations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.models import Organization, db
from keeper.testutils import MockTaskQueue

if TYPE_CHECKING:
    from unittest.mock import Mock

    from keeper.testutils import TestClient


def test_get_orgs(client: TestClient, mocker: Mock) -> None:
    task_queue = mocker.patch(
        "keeper.taskrunner.inspect_task_queue", return_value=None
    )
    task_queue = MockTaskQueue(mocker)  # noqa

    r = client.get("/v2/orgs")
    assert len(r.json) == 0

    # Create default organization
    org1 = Organization(
        slug="test1",
        title="Test1",
        root_domain="lsst.io",
        fastly_domain="global.ssl.fastly.net",
        bucket_name="bucket-name",
    )
    db.session.add(org1)
    db.session.commit()

    r = client.get("/v2/orgs")
    data = r.json
    assert len(data) == 1
    assert data[0]["slug"] == "test1"

    # Add another organization
    org2 = Organization(
        slug="test2",
        title="Test2",
        root_domain="lsst.io",
        fastly_domain="global.ssl.fastly.net",
        bucket_name="bucket-name",
    )
    db.session.add(org2)
    db.session.commit()

    r = client.get("/v2/orgs")
    data = r.json
    assert len(data) == 2

    # Try to get an organization resource from an item's self_url
    org_url = data[0]["self_url"]
    r2 = client.get(org_url)
    assert r2.json == data[0]
