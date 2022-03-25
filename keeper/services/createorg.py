"""A service for creating a new organization."""

from __future__ import annotations

from typing import Optional

from pydantic import SecretStr

from keeper.models import Organization, OrganizationLayoutMode, db


def create_organization(
    *,
    slug: str,
    title: str,
    layout: OrganizationLayoutMode,
    domain: str,
    path_prefix: str,
    bucket_name: str,
    s3_public_read: bool,
    fastly_support: bool,
    aws_id: Optional[str],
    aws_region: Optional[str],
    aws_secret: Optional[SecretStr],
    fastly_domain: Optional[str],
    fastly_service_id: Optional[str],
    fastly_api_key: Optional[SecretStr],
) -> Organization:
    """Create a new organization.

    The organization is automatically committed to the database and returned.
    """
    org = Organization(
        slug=slug,
        title=title,
        layout=layout,
        root_domain=domain,
        root_path_prefix=path_prefix,
        bucket_name=bucket_name,
        bucket_public_read=s3_public_read,
        aws_id=aws_id,
        aws_region=aws_region,
        fastly_support=fastly_support,
        fastly_domain=fastly_domain,
        fastly_service_id=fastly_service_id,
    )
    org.set_fastly_api_key(fastly_api_key)
    org.set_aws_secret_key(aws_secret)
    db.session.add(org)
    db.session.commit()
    return org
