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
    fastly_support: bool,
    fastly_domain: Optional[str],
    fastly_service_id: Optional[str],
    fastly_api_key: Optional[SecretStr],
) -> Organization:
    """Create a new organization.

    The organization is automatically committed to the database and returned.
    """
    encrypted_fastly_api_key = None  # TODO FIXME
    org = Organization(
        slug=slug,
        title=title,
        layout=layout,
        root_domain=domain,
        root_path_prefix=path_prefix,
        bucket_name=bucket_name,
        fastly_support=fastly_support,
        fastly_domain=fastly_domain,
        fastly_service_id=fastly_service_id,
        fastly_encrypted_api_key=encrypted_fastly_api_key,
    )
    db.session.add(org)
    db.session.commit()
    return org
