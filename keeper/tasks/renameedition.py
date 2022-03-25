"""Celery task for changing the name (URL slug) of an edition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger

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

    new_bucket_root_dir = edition.bucket_root_dirname

    organization = edition.product.organization
    aws_id = organization.aws_id
    aws_secret = organization.get_aws_secret_key()
    aws_region = organization.aws_region
    use_public_read_acl = organization.bucket_public_read
    if (
        aws_id is not None
        and aws_secret is not None
        and self.build is not None
    ):
        s3_service = s3.open_s3_resource(
            key_id=aws_id,
            access_key=aws_secret.get_secret_value(),
            aws_region=aws_region,
        )
        s3.copy_directory(
            s3=s3_service,
            bucket_name=self.product.bucket_name,
            src_path=old_bucket_root_dir,
            dest_path=new_bucket_root_dir,
            surrogate_key=self.surrogate_key,
            use_public_read_acl=use_public_read_acl,
        )
        s3.delete_directory(
            s3=s3_service,
            bucket_name=self.product.bucket_name,
            root_path=old_bucket_root_dir,
        )

    edition.pending_rebuild = False
    db.session.commit()


def mock_rename_edition(*, edition_id: int, new_slug: str) -> None:
    edition = Edition.query.get(edition_id)
    if edition.pending_rebuild is True:
        raise RuntimeError("Cannot rename edition while also rebuilding")
    edition.pending_rebuild = True
    edition.update_slug(new_slug)
    edition.pending_rebuild = False
    db.session.commit()
