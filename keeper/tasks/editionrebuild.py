"""Celery task for rebuilding an edition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests
from celery.utils.log import get_task_logger

from keeper import fastly, s3
from keeper.celery import celery_app
from keeper.models import Build, Edition, db
from keeper.utils import format_utc_datetime

if TYPE_CHECKING:
    import celery.task

__all__ = ["rebuild_edition", "send_edition_updated_event"]

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def rebuild_edition(
    self: celery.task.Task, edition_id: int, build_id: int
) -> None:
    """Rebuild an edition with a given build, as a Celery task.

    Parameters
    ----------
    edition_id : `int`
        Database ID of the edition resource.
    build_id : `int`
        Database ID of the build resource.

    Notes
    -----
    This task does the following:

    1. Sets the Edition.build property
    2. Toggles pending_rebuild to True
    1. Copies the new build into the edition's directory in the S3 bucket.
    2. Purge Fastly's cache for this edition.
    2. Send a ``edition.updated`` payload to LTD Events (if configured).
    """
    # LTD_EVENTS_URL = current_app.config["LTD_EVENTS_URL"]

    # api_url_parts = urlsplit(edition_url)
    # api_root = urlunsplit((api_url_parts[0], api_url_parts[1], "", "", ""))

    edition = Edition.query.get(edition_id)
    organization = edition.product.organization
    new_build = Build.query.get(build_id)

    logger.info(
        "Starting rebuild_edition for %s/%s/%s with build %s retry=%d",
        organization.slug,
        edition.product.slug,
        edition.slug,
        new_build.slug,
        self.request.retries,
    )

    aws_id = organization.aws_id
    aws_secret = organization.get_aws_secret_key()
    aws_region = organization.get_aws_region()
    use_public_read_acl = organization.get_bucket_public_read()

    fastly_service_id = organization.fastly_service_id
    fastly_key = organization.get_fastly_api_key()

    try:
        edition.set_pending_rebuild(new_build)

        if aws_id is not None and aws_secret is not None:
            logger.info(
                "Starting copy_directory %s to %s public_read=%s",
                new_build.bucket_root_dirname,
                edition.bucket_root_dirname,
                use_public_read_acl,
            )
            s3_service = s3.open_s3_resource(
                key_id=aws_id,
                access_key=aws_secret.get_secret_value(),
                aws_region=aws_region,
            )
            s3.copy_directory(
                s3=s3_service,
                bucket_name=edition.product.bucket_name,
                src_path=new_build.bucket_root_dirname,
                dest_path=edition.bucket_root_dirname,
                use_public_read_acl=use_public_read_acl,
                surrogate_key=edition.surrogate_key,
                # Force Fastly to cache the edition for 1 year
                surrogate_control="max-age=31536000",
                # Force browsers to revalidate their local cache using ETags.
                cache_control="no-cache",
            )
            logger.info("Finished copy_directory")
        else:
            logger.warning(
                "Skipping rebuild because AWS credentials are not set"
            )

        if (
            organization.fastly_support
            and fastly_service_id is not None
            and fastly_key is not None
        ):
            logger.info("Starting Fastly purge_key")
            fastly_service = fastly.FastlyService(
                fastly_service_id, fastly_key.get_secret_value()
            )
            fastly_service.purge_key(edition.surrogate_key)
            logger.info("Finished Fastly purge_key")
        else:
            logger.warning(
                "Skipping Fastly purge because credentials are not set"
            )

        edition.set_rebuild_complete()
        db.session.commit()

        # FIXME re-enable this. We need to provide a way to get the API route
        # to publish URLs to LTD Events
        # if LTD_EVENTS_URL is not None:
        #     send_edition_updated_event(edition, LTD_EVENTS_URL, api_root)
    except Exception:
        logger.exception("Error during copy")
        db.session.rollback()

        edition = Edition.query.get(edition_id)
        edition.pending_rebuild = False
        db.session.commit()

    logger.info("Finished rebuild_edition")


def send_edition_updated_event(
    edition: Edition, events_url: str, api_url: str
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
    logger.info("Sent edition.updated event to %s", events_url)
    if response.status_code != 200:
        message = (
            "Failure posting edition.updated event to %s. Got status %d. "
            "Reponse content: %s"
        )
        logger.warning(
            message, events_url, response.status_code, response.text
        )


def mock_rebuild_edition(*, edition_id: int, build_id: int) -> None:
    """Mock of `rebuild_edition` to apply database updates in tests."""
    edition = Edition.query.get(edition_id)
    new_build = Build.query.get(build_id)
    edition.set_pending_rebuild(new_build)
    edition.set_rebuild_complete()
    db.session.commit()
