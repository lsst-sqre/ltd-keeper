"""Filters for Jinja2 templates."""

from __future__ import annotations

__all__ = ["filter_simple_date"]

from datetime import datetime


def filter_simple_date(value: datetime) -> str:
    """Filter a `datetime.datetime` into a 'YYYY-MM-DD' string."""
    return value.strftime("%Y-%m-%d")
