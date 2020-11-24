from __future__ import annotations

from typing import TYPE_CHECKING

import requests
import structlog
from flask import current_app

from keeper.celery import celery_app
from keeper.exceptions import DasherError

if TYPE_CHECKING:
    import celery.task

__all__ = ["build_dashboard"]


@celery_app.task(bind=True)
def build_dashboard(self: celery.task.Task, product_url: str) -> None:
    """Build a product's dashboard as a Celery task.

    Parameters
    ----------
    product_url : `str`
        URL of the product resource.
    """
    logger = structlog.get_logger(__file__).bind(
        task=self.name,
        task_id=self.request.id,
        retry=self.request.retries,
        product_url=product_url,
    )
    logger.info("Starting dashboard build")

    dasher_url = current_app.config["LTD_DASHER_URL"]
    if dasher_url is None:
        # skip if not configured
        logger.warning("LTD_DASHER_URL not set, skipping")
        return

    dasher_build_url = "{0}/build".format(dasher_url)
    request_data = {"product_urls": [product_url]}
    r = requests.post(dasher_build_url, json=request_data)
    if r.status_code != 202:
        logger.warning(
            "Dashboard build failed",
            dasher_status=r.status_code,
            content=r.text,
        )
        raise DasherError("Dasher error (status {0})".format(r.status_code))

    logger.info("Finished dashboard build")
