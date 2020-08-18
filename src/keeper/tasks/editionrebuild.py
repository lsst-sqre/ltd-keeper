"""Celery task for rebuilding an edition.
"""

__all__ = ("rebuild_edition",)

from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from celery.utils.log import get_task_logger
from flask import current_app

from keeper.utils import format_utc_datetime

from .. import fastly, s3
from ..celery import celery_app
from ..models import Edition, db

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def rebuild_edition(self, edition_url, edition_id):
    """Rebuild an edition with a given build, as a Celery task.

    Parameters
    ----------
    edition_url : `str`
        Public URL of the edition resource.
    edition_id : `int`
        Database ID of the edition resource.

    Notes
    -----
    This task does the following:

    1. Copies the new build into the edition's directory in the S3 bucket.
    2. Purge Fastly's cache for this edition.
    2. Send a ``edition.updated`` payload to LTD Events (if configured).
    """
    logger.info(
        "Starting rebuild edition URL=%s retry=%d",
        edition_url,
        self.request.retries,
    )

    api_url_parts = urlsplit(edition_url)
    api_root = urlunsplit((api_url_parts[0], api_url_parts[1], "", "", ""))

    # edition = Edition.from_url(edition_url)
    edition = Edition.query.get(edition_id)
    build = edition.build

    FASTLY_SERVICE_ID = current_app.config["FASTLY_SERVICE_ID"]
    FASTLY_KEY = current_app.config["FASTLY_KEY"]
    AWS_ID = current_app.config["AWS_ID"]
    AWS_SECRET = current_app.config["AWS_SECRET"]
    LTD_EVENTS_URL = current_app.config["LTD_EVENTS_URL"]

    if AWS_ID is not None and AWS_SECRET is not None:
        logger.info("Starting copy_directory")
        s3.copy_directory(
            bucket_name=edition.product.bucket_name,
            src_path=build.bucket_root_dirname,
            dest_path=edition.bucket_root_dirname,
            aws_access_key_id=AWS_ID,
            aws_secret_access_key=AWS_SECRET,
            surrogate_key=edition.surrogate_key,
            # Force Fastly to cache the edition for 1 year
            surrogate_control="max-age=31536000",
            # Force browsers to revalidate their local cache using ETags.
            cache_control="no-cache",
        )
        logger.info("Finished copy_directory")
    else:
        logger.warning("Skipping rebuild because AWS credentials are not set")

    if FASTLY_SERVICE_ID is not None and FASTLY_KEY is not None:
        logger.info("Starting Fastly purge_key")
        fastly_service = fastly.FastlyService(FASTLY_SERVICE_ID, FASTLY_KEY)
        fastly_service.purge_key(edition.surrogate_key)
        logger.info("Finished Fastly purge_key")
    else:
        logger.warning("Skipping Fastly purge because credentials are not set")

    edition.set_rebuild_complete()
    db.session.commit()

    if LTD_EVENTS_URL is not None:
        send_edition_updated_event(edition, LTD_EVENTS_URL, api_root)

    logger.info("Finished rebuild_edition")


def send_edition_updated_event(edition, events_url, api_url):
    """Send the ``edition.updated`` event to the LTD Events webhook endpoint.
    """
    product_info = {
        "url": urljoin(api_url, "/products/{}".format(edition.product.slug)),
        "published_url": edition.product.published_url,
        "title": edition.product.title,
        "slug": edition.product.slug,
    }
    edition_info = {
        "url": urljoin(api_url, "/editions/{}".format(edition.id)),
        "published_url": edition.published_url,
        "title": edition.title,
        "slug": edition.slug,
        "build_url": urljoin(api_url, "/builds/{}".format(edition.build.id)),
    }
    event_info = {
        "event_type": "edition.updated",
        "event_timestamp": format_utc_datetime(edition.date_rebuilt),
        "edition": edition_info,
        "product": product_info,
    }

    response = requests.post(events_url, json=event_info)
    logger.info("Sent edition.updated event to %s", events_url)
    if response.status_code != 200:
        message = (
            "Failure posting edition.updated event to %s. Got status %d. "
            "Reponse content: %s"
        )
        logger.warning(
            message, events_url, response.status_code, response.text
        )
