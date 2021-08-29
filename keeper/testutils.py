"""Utilties for unit testing.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

from __future__ import annotations

import json
from base64 import b64encode
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from keeper.api._urls import build_from_url, edition_from_url, product_from_url
from keeper.tasks.registry import task_registry
from keeper.v2api._urls import product_from_url as product_from_v2_url

if TYPE_CHECKING:
    from unittest.mock import Mock

    from flask import Flask

__all__ = [
    "response",
    "TestClient",
    "MockTaskQueue",
]

response = namedtuple("response", "status headers json")


class TestClient:
    """TestClient wraps Flask's/Werkzeug's built-in testing client.

    The `get`, `post`, `put`, `delete` methods mirror HTTP
    commands and return a `response` `namedtuple` with fields:

    - `status`: the integer HTTP response code
    - `header`: the HTTP response headers
    - `json`: the return data, parse as JSON into a Python `dict` object.
    """

    def __init__(self, app: Flask, username: str, password: str = "") -> None:
        self.app = app
        self.auth = "Basic " + b64encode(
            (username + ":" + password).encode("utf-8")
        ).decode("utf-8")

    def send(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> response:
        # for testing, URLs just need to have the path and query string
        url_parsed = urlsplit(url)
        url = urlunsplit(
            ("", "", url_parsed.path, url_parsed.query, url_parsed.fragment)
        )

        # Append the authentication headers to all requests
        default_headers = {
            "Authorization": self.auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers is not None:
            default_headers.update(headers)
            headers = default_headers
        else:
            headers = default_headers

        # convert JSON data to a string
        if data:
            encoded_data = json.dumps(data)
        else:
            encoded_data = ""

        # send request to the test client and return the response
        with self.app.test_request_context(
            url, method=method, data=encoded_data, headers=headers
        ):
            rv = self.app.preprocess_request()
            if rv is None:
                rv = self.app.dispatch_request()
            rv = self.app.make_response(rv)
            rv = self.app.process_response(rv)
            return response(
                rv.status_code, rv.headers, json.loads(rv.data.decode("utf-8"))
            )

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> response:
        return self.send(url, "GET", headers=headers)

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
    ) -> response:
        return self.send(url, "POST", data, headers=headers)

    def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
    ) -> response:
        return self.send(url, "PUT", data, headers=headers)

    def patch(
        self,
        url: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
    ) -> response:
        return self.send(url, "PATCH", data, headers=headers)

    def delete(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> response:
        return self.send(url, "DELETE", headers=headers)


class MockTaskQueue:
    """A mocked task queue that can be inspected."""

    def __init__(self, mocker: Mock) -> None:
        self._mock = mocker.patch(
            "keeper.taskrunner.inspect_task_queue", return_value=None
        )
        self._registry = task_registry

    def assert_launched_once(self) -> None:
        """Assert that the task queue was launched only once."""
        self._mock.assert_called_once()

    def _get_tasks(self) -> List[Tuple[str, Dict[str, Any]]]:
        all_tasks: List[Tuple[str, Dict[str, Any]]] = []
        for call in self._mock.call_args_list:
            tasks = call[0][0]
            for task in tasks:
                all_tasks.append(task)
        return all_tasks

    def assert_task(
        self, command_name: str, data: Dict[str, Any], once: bool = True
    ) -> None:
        """Assert that a task was in the launched queue."""
        call_count = 0
        for task in self._get_tasks():
            if task[0] == command_name and task[1] == data:
                call_count += 1

        if once:
            if call_count == 1:
                return None
            else:
                raise AssertionError(
                    f"Task {command_name!r} with data {data!r} "
                    f"was launched {call_count} times (1 expected)."
                )
        else:
            if call_count > 0:
                return None
            else:
                raise AssertionError(
                    f"Task {command_name!r} with data {data!r} was not "
                    "launched."
                )

    def assert_dashboard_build_v1(
        self, product_url: str, once: bool = True
    ) -> None:
        product = product_from_url(product_url)
        self.assert_task(
            "build_dashboard", {"product_id": product.id}, once=once
        )

    def assert_dashboard_build_v2(
        self, product_url: str, once: bool = True
    ) -> None:
        product = product_from_v2_url(product_url)
        self.assert_task(
            "build_dashboard", {"product_id": product.id}, once=once
        )

    def assert_edition_build_v1(
        self, edition_url: str, build_url: str, once: bool = True
    ) -> None:
        edition = edition_from_url(edition_url)
        build = build_from_url(build_url)
        self.assert_task(
            "rebuild_edition",
            {"edition_id": edition.id, "build_id": build.id},
            once=once,
        )

    def assert_edition_rename_v1(
        self, edition_url: str, new_slug: str, once: bool = True
    ) -> None:
        edition = edition_from_url(edition_url)
        self.assert_task(
            "rebuild_edition",
            {"edition_id": edition.id, "new_slug": new_slug},
            once=once,
        )

    def apply_task_side_effects(self) -> None:
        for (task_name, task_args) in self._get_tasks():
            task = self._registry[task_name]
            task.test_mock(**task_args)
