"""Celery task for rebuilding an edition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
import structlog
from flask import current_app

from keeper import fastly, s3
from keeper.celery import celery_app
from keeper.models import Edition, db
from keeper.utils import format_utc_datetime

if TYPE_CHECKING:
    import celery.task

__all__ = ["rebuild_edition", "send_edition_updated_event"]


@celery_app.task(bind=True)
def rebuild_edition(
    self: celery.task.Task, edition_url: str, edition_id: int
) -> None:
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
    logger = structlog.get_logger(__file__).bind(
        task=self.name,
        task_id=self.request.id,
        retry=self.request.retries,
        edition_url=edition_url,
        edition_id=edition_id,
    )

    logger.info("Starting rebuild_edition")

    api_url_parts = urlsplit(edition_url)
    api_root = urlunsplit((api_url_parts[0], api_url_parts[1], "", "", ""))

    edition = Edition.query.get(edition_id)
    build = edition.build

    logger = logger.bind(product=edition.product.slug)

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

    logger.info("Setting rebuild_complete")
    edition.set_rebuild_complete()
    db.session.commit()
    logger.info("Finished setting rebuild_complete")

    if LTD_EVENTS_URL is not None:
        logger.info("Sending edition_updated event")
        send_edition_updated_event(edition, LTD_EVENTS_URL, api_root, logger)
        logger.info("Finished sending edition_updated event")

    logger.info("Finished rebuild_edition")


def send_edition_updated_event(
    edition: Edition,
    events_url: str,
    api_url: str,
    logger: structlog.BoundLogger,
) -> None:
    """Send the ``edition.updated`` event to the LTD Events webhook."""
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
    logger.info("Sent edition.updated event", events_url=events_url)
    if response.status_code != 200:
        message = "Failure posting edition.updated event."
        logger.warning(
            message,
            events_url=events_url,
            status=response.status_code,
            content=response.text,
        )
