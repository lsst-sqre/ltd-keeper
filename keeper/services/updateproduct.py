from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.models import db
from keeper.taskrunner import queue_task_command

if TYPE_CHECKING:
    from keeper.models import Product


def update_product(
    *, product: Product, new_doc_repo: Optional[str], new_title: Optional[str]
) -> Product:
    """Modify an existing product.

    The updated product is added to the current database session and
    committed. A dashboard rebuild task is also appended to the task chain.
    The caller is responsible for launching the celery task.

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
    db.session.commit()

    queue_task_command(
        command="build_dashboard", data={"product_id": product.id}
    )

    return product
