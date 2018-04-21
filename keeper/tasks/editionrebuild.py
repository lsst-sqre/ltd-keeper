"""Celery task for rebuilding an edition.
"""

__all__ = ('rebuild_edition',)

from celery.utils.log import get_task_logger
from flask import current_app

from ..celery import celery_app
from ..models import db, Edition
from .. import s3
from .. import fastly


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
    """
    logger.info('Starting rebuild edition URL=%s retry=%d',
                edition_url, self.request.retries)

    # edition = Edition.from_url(edition_url)
    edition = Edition.query.get(edition_id)
    build = edition.build

    FASTLY_SERVICE_ID = current_app.config['FASTLY_SERVICE_ID']
    FASTLY_KEY = current_app.config['FASTLY_KEY']
    AWS_ID = current_app.config['AWS_ID']
    AWS_SECRET = current_app.config['AWS_SECRET']

    if AWS_ID is not None and AWS_SECRET is not None:
        logger.info('Starting copy_directory')
        s3.copy_directory(
            bucket_name=edition.product.bucket_name,
            src_path=build.bucket_root_dirname,
            dest_path=edition.bucket_root_dirname,
            aws_access_key_id=AWS_ID,
            aws_secret_access_key=AWS_SECRET,
            surrogate_key=edition.surrogate_key,
            # Force Fastly to cache the edition for 1 year
            surrogate_control='max-age=31536000',
            # Force browsers to revalidate their local cache using ETags.
            cache_control='no-cache')
        logger.info('Finished copy_directory')
    else:
        logger.warning('Skipping rebuild because AWS credentials are not set')

    if FASTLY_SERVICE_ID is not None and FASTLY_KEY is not None:
        logger.info('Starting Fastly purge_key')
        fastly_service = fastly.FastlyService(
            FASTLY_SERVICE_ID,
            FASTLY_KEY)
        fastly_service.purge_key(edition.surrogate_key)
        logger.info('Finished Fastly purge_key')
    else:
        logger.warning('Skipping Fastly purge because credentials are not set')

    edition.set_rebuild_complete()
    db.session.commit()

    logger.info('Finished rebuild_edition')
