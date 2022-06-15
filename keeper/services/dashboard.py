"""This service updates project's edition and build dashboards."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

import boto3
from ltdconveyor.s3 import (
    create_dir_redirect_object,
    upload_dir,
    upload_object,
)

from keeper import fastly, s3
from keeper.dashboard.context import Context
from keeper.dashboard.templateproviders import BuiltinTemplateProvider

if TYPE_CHECKING:
    from keeper.models import Product

__all__ = ["build_dashboard"]


def build_dashboard(product: Product, logger: Any) -> None:
    """Build a dashboard (run from a Celery task)."""
    logger.debug("In build_dashboard service function.")

    organization = product.organization

    aws_id = organization.aws_id
    aws_secret = organization.get_aws_secret_key()
    aws_region = organization.get_aws_region()
    use_public_read_acl = organization.get_bucket_public_read()

    fastly_service_id = organization.fastly_service_id
    fastly_key = organization.get_fastly_api_key()

    # Render dashboards using the built-in dashboard template provider;
    # eventually we'll add the ability to get templates from a configured
    # S3 bucket location.
    context = Context.create(product)
    template_provider = BuiltinTemplateProvider()
    edition_html = template_provider.render_edition_dashboard(
        project_context=context.project_context,
        edition_contexts=context.edition_contexts,
    )
    build_html = template_provider.render_build_dashboard(
        project_context=context.project_context,
        build_contexts=context.build_contexts,
    )

    if aws_id is not None and aws_secret is not None:
        s3_service = s3.open_s3_resource(
            key_id=aws_id,
            access_key=aws_secret.get_secret_value(),
            aws_region=aws_region,
        )

        upload_dir(
            product.organization.bucket_name,
            f"{product.slug}/_dashboard-assets",
            str(template_provider.static_dir),
            upload_dir_redirect_objects=True,
            surrogate_key=product.surrogate_key,
            surrogate_control="max-age=31536000",
            cache_control="no-cache",
            acl="public-read" if use_public_read_acl else None,
            aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret,
        )

        upload_dashboard_html(
            html=edition_html,
            key="v/index.html",
            product=product,
            s3_service=s3_service,
        )
        upload_dashboard_html(
            html=build_html,
            key="builds/index.html",
            product=product,
            s3_service=s3_service,
        )

    else:
        logger.warning(
            "Skipping dashboard uploads because AWS credentials are not set"
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
        fastly_service.purge_key(product.surrogate_key)
        logger.info("Finished Fastly purge_key")
    else:
        logger.warning("Skipping Fastly purge because credentials are not set")


def upload_dashboard_html(
    *,
    html: str,
    key: str,
    product: Product,
    s3_service: boto3.resources.base.ServiceResource,
) -> None:
    bucket = s3_service.Bucket(product.organization.bucket_name)

    if not key.startswith("/"):
        key = f"/{key}"

    object_path = f"{product.slug}{key}"

    # Have Fastly cache the dashboard for a year (or until purged)
    metadata = {
        "surrogate-key": product.surrogate_key,
        "surrogate-control": "max-age=31536000",
    }
    acl = "public-read"
    # Have the *browser* never cache the dashboard
    cache_control = "no-cache"

    # Upload HTML object
    upload_object(
        object_path,
        bucket,
        content=html,
        metadata=metadata,
        acl=acl,
        cache_control=cache_control,
        content_type="text/html",
    )

    # Upload directory redirect object
    bucket_dir_path = PurePosixPath(object_path).parent
    create_dir_redirect_object(
        bucket_dir_path,
        bucket,
        metadata=metadata,
        acl=acl,
        cache_control=cache_control,
    )
