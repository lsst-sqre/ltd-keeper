from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional, Tuple

import keeper.route53
from keeper.models import OrganizationLayoutMode, Product, db

from .createedition import create_edition
from .requestdashboardbuild import request_dashboard_build

if TYPE_CHECKING:
    from keeper.models import Edition, Organization


def create_product(
    *,
    org: Organization,
    slug: str,
    doc_repo: str,
    title: str,
    default_edition_mode: Optional[str] = None,
) -> Tuple[Product, Edition]:
    """Create a new product, along with its main edition.

    The product and edition are added to the current database session and
    committed. A dashboard rebuild task is also appended to the task chain.
    The caller is responsible for launching the celery task.

    The route 53 CNAME for the product is also created via `configure_cname`.

    Parameters
    ----------
    org : `keeper.models.Organization`
        The organization that owns the product.
    slug : `str`
        The URL-safe string that identifies the product, both in the API
        and on the web as a subdomain or URL path.
    doc_repo : `str`
        The URL of the product's associated source repository.
    title : `str`
        The human-readable name of the product.
    default_edition_mode : str, optional
        The string name of the tracking mode for the default (main) edition.
        If left None, defaults to `keeper.models.Edition.default_mode_name`.

    Returns
    -------
    product : `keeper.models.Product`
        The product entity, already added to the DB session.
    edition : `keeper.models.Edition`
        The main edition of the product, already added to the DB session.
    """
    product = Product(organization=org, surrogate_key=uuid.uuid4().hex)
    product.slug = slug
    product.doc_repo = doc_repo
    product.title = title
    # Compatibility with v1 table architecture. This can be removed once
    # these fields are dropped from the Product model
    # print(f"create_product {org.root_domain}")
    product.root_domain = org.root_domain
    product.root_fastly_domain = org.fastly_domain
    product.bucket_name = org.bucket_name

    if org.layout == OrganizationLayoutMode.subdomain:
        configure_subdomain(product)

    db.session.add(product)
    db.session.flush()  # Because Edition._validate_slug does not autoflush

    # Create a default edition
    edition = create_edition(
        product=product,
        tracking_mode=default_edition_mode,
        slug="__main",
        title="Latest",
    )
    db.session.add(edition)
    db.session.commit()

    request_dashboard_build(product)

    return product, edition


def configure_subdomain(product: Product) -> None:
    """Configure the subdomain CNAME for a product with route53.

    Parameters
    ----------
    product : `keeper.models.Product`
        The product entity, already added to the DB session.
    """
    organization = product.organization
    aws_id = organization.aws_id
    aws_secret = organization.get_aws_secret_key()
    if product.fastly_domain is None:
        raise RuntimeError(
            "Fastly domain is not set on subdomain-based layout."
        )
    if aws_id is not None and aws_secret is not None:
        keeper.route53.create_cname(
            product.domain,
            product.fastly_domain,
            aws_id,
            aws_secret.get_secret_value(),
        )
