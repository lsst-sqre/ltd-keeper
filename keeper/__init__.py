"""Application initialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keeper.appfactory import create_flask_app
from keeper.version import get_version

if TYPE_CHECKING:
    from flask import Flask

__all__ = ["__version__", "flask_app"]

__version__: str = get_version()

flask_app: Flask = create_flask_app()
