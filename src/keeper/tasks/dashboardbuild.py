__all__ = ("build_dashboard",)

import requests
from celery.utils.log import get_task_logger
from flask import current_app

from ..celery import celery_app
from ..exceptions import DasherError

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def build_dashboard(self, product_url):
    """Build a product's dashboard as a Celery task.

    Parameters
    ----------
    product_url : `str`
        URL of the product resource.
    """
    logger.info(
        "Starting dashboard build URL=%s retry=%d",
        product_url,
        self.request.retries,
    )

    dasher_url = current_app.config["LTD_DASHER_URL"]
    if dasher_url is None:
        # skip if not configured
        logger.warning("LTD_DASHER_URL not set, skipping")
        return

    dasher_build_url = "{0}/build".format(dasher_url)
    request_data = {"product_urls": [product_url]}
    r = requests.post(dasher_build_url, json=request_data)
    if r.status_code != 202:
        raise DasherError("Dasher error (status {0})".format(r.status_code))

    logger.info("Finished triggering dashboard build")
