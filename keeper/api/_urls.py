"""Functions for creating URLs for ORM resources as their GET endpoints
in the v1 API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import url_for

if TYPE_CHECKING:
    import celery

    from keeper.models import Build, Edition


def url_for_edition(edition: Edition) -> str:
    return url_for("api.get_edition", id=edition.id, _external=True)


def url_for_build(build: Build) -> str:
    return url_for("api.get_build", id=build.id, _external=True)


def url_for_task(task: celery.Task) -> str:
    return url_for("api.get_task_status", id=task.id, _external=True)
