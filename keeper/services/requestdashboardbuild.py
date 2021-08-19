"""This services queues a dashboard build for a product."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.taskrunner import queue_task_command

if TYPE_CHECKING:
    from keeper.models import Product

__all__ = ["request_dashboard_build"]


def request_dashboard_build(product: Product) -> None:
    """Create a celery task to build a dashboard for a product."""
    queue_task_command(
        command="build_dashboard", data={"product_id": product.id}
    )
