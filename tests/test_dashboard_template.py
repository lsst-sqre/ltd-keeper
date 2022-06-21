"""Test the built-in dashboard template by rendering to a local directory."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from keeper.dashboard.context import (
    BuildContext,
    BuildContextList,
    EditionContext,
    EditionContextList,
    ProjectContext,
)
from keeper.dashboard.templateproviders import BuiltinTemplateProvider
from keeper.models import EditionKind


def test_templates() -> None:
    output_dir = Path(__file__).parent.parent.joinpath("dashboard_dev")

    # Create mock data
    project = ProjectContext(
        title="LTD Test Project",
        source_repo_url="https://github.com/lsst-sqre/ltd-keeper",
        url="https://example.com/ltd-test/",
    )
    editions: List[EditionContext] = []
    builds: List[BuildContext] = []

    editions.append(
        EditionContext(
            title="Current",
            url="https://example.com/ltd-test/",
            date_updated=datetime(2022, 6, 21, tzinfo=timezone.utc),
            kind=EditionKind.main,
            slug="__main",
            git_ref="main",
        )
    )

    builds.append(
        BuildContext(
            slug="1",
            url="https://example.com/ltd-test/builds/1",
            git_ref="main",
            date=datetime(2022, 6, 21, tzinfo=timezone.utc),
        )
    )

    template = BuiltinTemplateProvider()
    template.render_locally(
        directory=output_dir,
        project_context=project,
        edition_contexts=EditionContextList(editions),
        build_contexts=BuildContextList(builds),
    )
