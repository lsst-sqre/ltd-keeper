"""Celery task for changing the name (URL slug) of an edition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger
from flask import current_app

from keeper import s3
from keeper.celery import celery_app
from keeper.models import Edition, db

if TYPE_CHECKING:
    import celery.task

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def rename_edition(
    self: celery.task.Task, edition_id: int, new_slug: str
) -> None:
    logger.info(
        "Starting rebuild edition edition_id=%s retry=%d",
        edition_id,
        self.request.retries,
    )

    edition = Edition.query.get(edition_id)
    if edition.pending_rebuild is True:
        raise RuntimeError("Cannot rename edition while also rebuilding")

    edition.pending_rebuild = True
    db.session.commit()

    old_bucket_root_dir = edition.bucket_root_dirname

    edition.update_slug(new_slug)

    new_bucket_root_dir = self.bucket_root_dirname

    AWS_ID = current_app.config["AWS_ID"]
    AWS_SECRET = current_app.config["AWS_SECRET"]
    if (
        AWS_ID is not None
        and AWS_SECRET is not None
        and self.build is not None
    ):
        s3.copy_directory(
            self.product.bucket_name,
            old_bucket_root_dir,
            new_bucket_root_dir,
            AWS_ID,
            AWS_SECRET,
            surrogate_key=self.surrogate_key,
        )
        s3.delete_directory(
            self.product.bucket_name,
            old_bucket_root_dir,
            AWS_ID,
            AWS_SECRET,
        )

    edition.pending_rebuild = False
    db.session.commit()
