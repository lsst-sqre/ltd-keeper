"""Utilities for the Flask API and SQLAlchemy models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

from __future__ import annotations

import json
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    SupportsIndex,
    Tuple,
    Union,
)

from dateutil import parser as datetime_parser
from dateutil.tz import tzutc
from flask.globals import _app_ctx_stack, _request_ctx_stack
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import VARCHAR, TypeDecorator
from werkzeug.exceptions import NotFound
from werkzeug.urls import url_parse

from keeper.exceptions import ValidationError

if TYPE_CHECKING:
    import datetime

__all__ = [
    "PRODUCT_SLUG_PATTERN",
    "PATH_SLUG_PATTERN",
    "TICKET_BRANCH_PATTERN",
    "split_url",
    "validate_product_slug",
    "validate_path_slug",
    "auto_slugify_edition",
    "format_utc_datetime",
    "parse_utc_datetime",
    "JSONEncodedVARCHAR",
    "MutableList",
]

PRODUCT_SLUG_PATTERN = re.compile(r"^[a-z]+[-a-z0-9]*[a-z0-9]+$")
"""Regular expression to validate url-safe slugs for products."""

PATH_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9-\._]+$")
"""Regular expression to validate url-safe slugs for editions/builds."""

TICKET_BRANCH_PATTERN = re.compile(r"^tickets/([A-Z]+-[0-9]+)$")
"""Regular expression for DM ticket branches (to auto-build slugs)."""


def split_url(url: str, method: str = "GET") -> Tuple[str, Dict[str, str]]:
    """Returns the endpoint name and arguments that match a given URL.

    This is the reverse of Flask's `url_for()`.
    """
    appctx = _app_ctx_stack.top
    reqctx = _request_ctx_stack.top
    if appctx is None:
        raise RuntimeError(
            "Attempted to match a URL without the "
            "application context being pushed. This has to be "
            "executed when application context is available."
        )

    if reqctx is not None:
        url_adapter = reqctx.url_adapter
    else:
        url_adapter = appctx.url_adapter
        if url_adapter is None:
            raise RuntimeError(
                "Application was not able to create a URL "
                "adapter for request independent URL matching. "
                "You might be able to fix this by setting "
                "the SERVER_NAME config variable."
            )
    parsed_url = url_parse(url)
    if (
        parsed_url.netloc != ""
        and parsed_url.netloc != url_adapter.server_name
    ):
        raise ValidationError("Invalid URL: " + url)
    try:
        result = url_adapter.match(parsed_url.path, method)
    except NotFound:
        raise ValidationError("Invalid URL: " + url)
    return result


def validate_product_slug(slug: str) -> bool:
    """Validate a URL-safe slug for products."""
    m = PRODUCT_SLUG_PATTERN.match(slug)
    if m is None or m.string != slug:
        raise ValidationError("Invalid slug: " + slug)
    return True


def validate_path_slug(slug: str) -> bool:
    """Validate a URL-safe slug for builds/editions.

    This validation is slightly more lax than `validate_product_slug` because
    build/edition slugs are only used in the paths, not as parts of domains.
    """
    m = PATH_SLUG_PATTERN.match(slug)
    if m is None or m.string != slug:
        raise ValidationError("Invalid slug: " + slug)
    return True


def auto_slugify_edition(git_refs: List[str]) -> str:
    """Given a list of Git refs, build a reasonable URL-safe slug."""
    slug = "-".join(git_refs)

    # Customization for making slugs from DM ticket branches
    # Ideally we'd add a more formal API for adding similar behaviours
    m = TICKET_BRANCH_PATTERN.match(slug)
    if m is not None:
        return m.group(1)

    slug = slug.replace("/", "-")
    return slug


def format_utc_datetime(dt: Optional[datetime.datetime]) -> Optional[str]:
    """Standardized UTC `str` representation for a `datetime.datetime`."""
    if dt is None:
        return None
    else:
        return dt.isoformat() + "Z"


def parse_utc_datetime(
    datetime_str: Optional[str],
) -> Optional[datetime.datetime]:
    """Parse a date string, returning a UTC datetime object."""
    if datetime_str is not None:
        date = (
            datetime_parser.parse(datetime_str)
            .astimezone(tzutc())
            .replace(tzinfo=None)
        )
        return date
    else:
        return None


class JSONEncodedVARCHAR(TypeDecorator):
    """Custom column JSON datatype that's persisted as a JSON string.

    Example::

        col = db.Column(JSONEncodedVARCHAR(1024))

    Adapted from SQLAlchemy example code: http://ls.st/4ad
    """

    impl = VARCHAR

    def process_bind_param(self, value: Any, dialect: Any) -> str:
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Any:
        if value is not None:
            value = json.loads(value)
        return value


class MutableList(Mutable, list):
    """Wrapper for a JSONEncodedVARCHAR column to allow an underlying list
    type to be mutable.

    Example::

        col = db.Column(MutableList.as_mutable(JSONEncodedVARCHAR(1024)))

    Adapted from SQLAlchemy docs: http://ls.st/djv
    """

    @classmethod
    def coerce(cls, key: Any, value: Any) -> "MutableList":
        """Convert plain lists to MutableList."""
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, index: Any, value: Any) -> None:
        """Detect list set events and emit change events."""
        list.__setitem__(self, index, value)
        self.changed()

    def __delitem__(self, index: Union[SupportsIndex, slice]) -> None:
        """Detect list del events and emit change events."""
        list.__delitem__(self, index)
        self.changed()
