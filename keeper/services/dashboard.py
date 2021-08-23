"""This service updates an edition's dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from keeper.models import Product

__all__ = ["build_dashboard"]


def build_dashboard(product: Product, logger: Any) -> None:
    """Build a dashboard (run from a Celery task)."""
    # TODO implement this service
    logger.debug("In build_dashboard service function.")
