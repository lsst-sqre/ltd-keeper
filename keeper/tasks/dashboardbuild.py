from __future__ import annotations

from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger

from keeper.celery import celery_app
from keeper.models import Product
from keeper.services.dashboard import build_dashboard as build_dashboard_svc

if TYPE_CHECKING:
    import celery.task

__all__ = ["build_dashboard"]

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def build_dashboard(self: celery.task.Task, product_id: str) -> None:
    """Build a product's dashboard as a Celery task.

    Parameters
    ----------
    product_url : `str`
        URL of the product resource.
    """
    logger.info(
        "Starting dashboard build product_id=%s retry=%d",
        product_id,
        self.request.retries,
    )

    product = Product.query.get(product_id)
    build_dashboard_svc(product, logger)

    logger.info("Finished triggering dashboard build")
