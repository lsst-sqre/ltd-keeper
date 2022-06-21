"""Providers load templates from specific sources and provider a
Jinja2 rendering environment.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import jinja2

from .context import BuildContextList, EditionContextList, ProjectContext
from .jinjafilters import filter_simple_date


class BuiltinTemplateProvider:
    """A template provider for Keeper's built in dashboard templates."""

    def __init__(self) -> None:
        self.template_dir = Path(__file__).parent.joinpath("template")
        self.static_dir = Path(__file__).parent.joinpath("static")

        self.jinja_env = self._create_environment()

    def _create_environment(self) -> jinja2.Environment:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        env.filters["simple_date"] = filter_simple_date
        return env

    def render_edition_dashboard(
        self,
        *,
        project_context: ProjectContext,
        edition_contexts: EditionContextList,
    ) -> str:
        template = self.jinja_env.get_template("edition_dashboard.jinja")
        return template.render(
            project=project_context,
            editions=edition_contexts,
            asset_dir="../_dashboard-assets",
        )

    def render_build_dashboard(
        self,
        *,
        project_context: ProjectContext,
        build_contexts: BuildContextList,
    ) -> str:
        template = self.jinja_env.get_template("build_dashboard.jinja")
        return template.render(
            project=project_context,
            builds=build_contexts,
            asset_dir="../_dashboard-assets",
        )

    def render_locally(
        self,
        *,
        directory: Path,
        project_context: ProjectContext,
        edition_contexts: EditionContextList,
        build_contexts: BuildContextList,
        clobber: bool = True,
    ) -> None:
        """Render the dashboard into a local directory for testing."""
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()
        assets_dir = directory.joinpath("_dashboard-assets")
        # assets_dir.mkdir()
        v_dir = directory.joinpath("v")
        v_dir.mkdir()
        builds_dir = directory.joinpath("builds")
        builds_dir.mkdir()

        shutil.copytree(self.static_dir, assets_dir)

        edition_dashboard = self.render_edition_dashboard(
            project_context=project_context,
            edition_contexts=edition_contexts,
        )
        v_html_path = v_dir.joinpath("index.html")
        v_html_path.write_text(edition_dashboard)

        build_dashboard = self.render_build_dashboard(
            project_context=project_context, build_contexts=build_contexts
        )
        build_html_path = builds_dir.joinpath("index.html")
        build_html_path.write_text(build_dashboard)
