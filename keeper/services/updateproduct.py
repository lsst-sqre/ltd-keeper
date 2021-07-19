from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.api._urls import url_for_product  # FIXME refactor arg for tasks
from keeper.models import db
from keeper.taskrunner import append_task_to_chain, mock_registry
from keeper.tasks.dashboardbuild import build_dashboard

if TYPE_CHECKING:
    from keeper.models import Product


# Register imports of celery task chain launchers
mock_registry.extend(
    [
        "keeper.services.updateproduct.append_task_to_chain",
    ]
)


def update_product(
    *, product: Product, new_doc_repo: Optional[str], new_title: Optional[str]
) -> Product:
    """Modify an existing product.

    The updated product is added to the current database session. A
    dashboard rebuild task is also appended to the task chain. The caller is
    responsible for committing the database session and launching the celery
    task.

    Parameters
    ----------
    product : `keeper.models.Product`
        The product.
    new_doc_repo : `str`
        The URL of the product's associated source repository.
    new_title : `str`
        The human-readable name of the product.

    Returns
    -------
    product : `keeper.models.Product`
        The product entity, already added to the DB session.
    """
    if new_doc_repo is not None:
        product.doc_repo = new_doc_repo

    if new_title is not None:
        product.title = new_title

    db.session.add(product)

    product_url = url_for_product(product)
    append_task_to_chain(build_dashboard.si(product_url))

    return product
