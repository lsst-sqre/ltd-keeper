from __future__ import annotations

import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from structlog import get_logger

from keeper.auth import is_authorized
from keeper.exceptions import ValidationError
from keeper.models import Build, Edition, Permission, db
from keeper.s3 import (
    format_bucket_prefix,
    open_s3_resource,
    presign_post_url_for_directory_object,
    presign_post_url_for_prefix,
)
from keeper.utils import auto_slugify_edition, validate_path_slug

from .createedition import create_edition

if TYPE_CHECKING:
    import boto3

    from keeper.models import Product


def create_build(
    *,
    product: Product,
    git_ref: str,
    github_requester: Optional[str] = None,
    slug: Optional[str] = None,
) -> Tuple[Build, Optional[Edition]]:
    """Create a new build.

    The build is added to the current database session and committed.

    Parameters
    ----------
    product : `keeper.models.Product`
        The product that owns this build and edition.
    git_ref : `str`
        The git ref associated with this build or edition.
    github_requester : `str`, optional
        The GitHub username of the person that created the build.
    slug : `str`, optional
        The build's slug. If a slug is not provided, one is created
        automatically. The most common case is allow builds to be automatically
        named.

    Returns
    -------
    build : `keeper.models.Build`
        The build entity, already added to the DB session.
    edition : `keeper.models.Edition`, optional
        The edition entity, already added to the DB session, if one was created
        to automatically track the build's ``git_ref``.
    """
    logger = get_logger(__name__)

    build = Build(
        product=product,
        surrogate_key=uuid.uuid4().hex,
        git_ref=git_ref,
        git_refs=[git_ref],  # set for schema migration
    )

    if github_requester is not None:
        build.github_requester = github_requester

    if slug is None:
        build.slug = _auto_create_slug(product)
        logger.debug("Automatically created build slug", slug=build.slug)
    else:
        builds_with_slug = (
            Build.query.autoflush(False)
            .filter(Build.product == product)
            .filter(Build.slug == slug)
            .count()
        )
        if builds_with_slug > 0:
            raise ValidationError(f"A build already exists with slug {slug!r}")
        build.slug = slug

    db.session.add(build)
    db.session.commit()

    # Create an edition to track this git ref if necessary
    edition = create_autotracking_edition(product=product, build=build)

    return build, edition


def _auto_create_slug(product: Product) -> str:
    """Automatically create a unique build slug for this product."""
    all_builds = (
        Build.query.autoflush(False).filter(Build.product == product).all()
    )
    slugs = [b.slug for b in all_builds]
    trial_slug_n = 1
    while str(trial_slug_n) in slugs:
        trial_slug_n += 1
    slug = str(trial_slug_n)

    validate_path_slug(slug)

    return slug


def create_autotracking_edition(
    *, product: Edition, build: Build
) -> Optional[Edition]:
    """Create an edition that tracks the git_ref of the build.

    The edition is added to the current database session and committed.

    Parameters
    ----------
    product : `keeper.models.Product`
        The product that owns this build and edition.
    build : `keeper.models.Build`
        The build, which is associated with a ``git_ref``.

    Returns
    -------
    edition : `keeper.models.Edition` or `None`
        Returns the edition if one was created, or `None` if a new edition did
        not need to be created.
    """
    logger = get_logger(__name__)

    edition_count = (
        Edition.query.filter(Edition.product == product)
        .filter(Edition.tracked_refs == build.git_refs)
        .count()
    )
    if edition_count == 0 and is_authorized(Permission.ADMIN_EDITION):
        try:
            edition_slug = auto_slugify_edition([build.git_ref])
            edition = create_edition(
                product=product,
                title=edition_slug,
                slug=edition_slug,
                tracking_mode="git_ref",
                tracked_ref=build.git_ref,
            )
            db.session.add(edition)
            db.session.commit()

            logger.info(
                "Created edition because of a build",
                slug=edition.slug,
                id=edition.id,
                tracked_ref=edition.tracked_ref,
            )
            return edition
        except Exception:
            logger.exception("Error while automatically creating an edition")
            db.session.rollback()
            return None
    else:
        logger.info(
            "Did not create a new edition because of a build",
            authorized=is_authorized(Permission.ADMIN_EDITION),
            edition_count=edition_count,
        )
        return None


def create_presigned_post_urls(
    *, build: Build, directories: List[str]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    logger = get_logger(__name__)

    organization = build.product.organization
    aws_id = organization.aws_id
    aws_secret = organization.get_aws_secret_key()
    aws_region = organization.aws_region
    use_public_read_acl = organization.bucket_public_read

    s3_service = open_s3_resource(
        key_id=aws_id,
        access_key=aws_secret.get_secret_value() if aws_secret else "",
        aws_region=aws_region,
    )
    presigned_prefix_urls = {}
    presigned_dir_urls = {}
    for d in set(directories):
        bucket_prefix = format_bucket_prefix(build.bucket_root_dirname, d)
        dir_key = bucket_prefix.rstrip("/")

        presigned_prefix_url = _create_presigned_url_for_prefix(
            s3=s3_service,
            bucket_name=build.product.bucket_name,
            prefix=bucket_prefix,
            surrogate_key=build.surrogate_key,
            use_public_read_acl=use_public_read_acl,
        )
        presigned_prefix_urls[d] = deepcopy(presigned_prefix_url)

        presigned_dir_url = _create_presigned_url_for_directory(
            s3=s3_service,
            bucket_name=build.product.bucket_name,
            key=dir_key,
            surrogate_key=build.surrogate_key,
            use_public_read_acl=use_public_read_acl,
        )
        presigned_dir_urls[d] = deepcopy(presigned_dir_url)

    logger.info(
        "Created presigned POST URLs for prefixes",
        post_urls=presigned_prefix_urls,
    )
    logger.info(
        "Created presigned POST URLs for dirs", post_urls=presigned_dir_urls
    )

    return presigned_prefix_urls, presigned_dir_urls


def _create_presigned_url_for_prefix(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    prefix: str,
    surrogate_key: str,
    use_public_read_acl: bool,
) -> Dict[str, Any]:
    # These conditions become part of the URL's presigned policy
    url_conditions = [
        {"Cache-Control": "max-age=31536000"},
        # Make sure the surrogate-key is always consistent
        {"x-amz-meta-surrogate-key": surrogate_key},
        # Allow any Content-Type header
        ["starts-with", "$Content-Type", ""],
        # This is the default. It means for a success (204), no content
        # is returned by S3. This is what we want.
        {"success_action_status": "204"},
    ]
    if use_public_read_acl:
        url_conditions.append({"acl": "public-read"})
    # These fields are pre-populated for clients
    url_fields = {
        "Cache-Control": "max-age=31536000",
        "x-amz-meta-surrogate-key": surrogate_key,
        "success_action_status": "204",
    }
    if use_public_read_acl:
        url_fields["acl"] = "public-read"
    return presign_post_url_for_prefix(
        s3=s3,
        bucket_name=bucket_name,
        prefix=prefix,
        expiration=3600,
        conditions=url_conditions,
        fields=url_fields,
    )


def _create_presigned_url_for_directory(
    *,
    s3: boto3.resources.base.ServiceResource,
    bucket_name: str,
    key: str,
    surrogate_key: str,
    use_public_read_acl: bool,
) -> Dict[str, Any]:
    # These conditions become part of the URL's presigned policy
    url_conditions = [
        {"Cache-Control": "max-age=31536000"},
        # Make sure the surrogate-key is always consistent
        {"x-amz-meta-surrogate-key": surrogate_key},
        # This is the default. It means for a success (204), no content
        # is returned by S3. This is what we want.
        {"success_action_status": "204"},
    ]
    if use_public_read_acl:
        url_conditions.append({"acl": "public-read"})
    url_fields = {
        "Cache-Control": "max-age=31536000",
        "x-amz-meta-surrogate-key": surrogate_key,
        "success_action_status": "204",
    }
    if use_public_read_acl:
        url_fields["acl"] = "public-read"
    return presign_post_url_for_directory_object(
        s3=s3,
        bucket_name=bucket_name,
        key=key,
        fields=url_fields,
        conditions=url_conditions,
        expiration=3600,
    )
