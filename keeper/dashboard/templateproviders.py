"""Providers load templates from specific sources and provider a
Jinja2 rendering environment.
"""

from __future__ import annotations

from pathlib import Path

import jinja2

from .context import BuildContextList, EditionContextList, ProjectContext
from .jinjafilters import filter_simple_date


class BuiltinTemplateProvider:
    """A template provider for Keeper's built in dashboard templates."""

    def __init__(self) -> None:
        self.template_dir = Path(__file__).parent.joinpath("template")
        self.static_dir = self.template_dir.joinpath("static")

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
