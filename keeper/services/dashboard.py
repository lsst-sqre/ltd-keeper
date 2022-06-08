"""This service updates project's edition and build dashboards."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from keeper.dashboard.context import Context
from keeper.dashboard.templateproviders import BuiltinTemplateProvider

if TYPE_CHECKING:
    from keeper.models import Product

__all__ = ["build_dashboard"]


def build_dashboard(product: Product, logger: Any) -> None:
    """Build a dashboard (run from a Celery task)."""
    logger.debug("In build_dashboard service function.")

    context = Context.create(product)
    template_provider = BuiltinTemplateProvider()
    print(
        template_provider.render_edition_dashboard(
            project_context=context.project_context,
            edition_contexts=context.edition_contexts,
        )
    )
    print(
        template_provider.render_build_dashboard(
            project_context=context.project_context,
            build_contexts=context.build_contexts,
        )
    )
