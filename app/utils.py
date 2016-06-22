"""Utilities for the Flask API and SQLAlchemy models.

Copyright 2016 AURA/LSST.
Copyright 2014 Miguel Grinberg.
"""

import re
from dateutil import parser as datetime_parser
from dateutil.tz import tzutc
import json

from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.ext.mutable import Mutable

from flask.globals import _app_ctx_stack, _request_ctx_stack
from werkzeug.urls import url_parse
from werkzeug.exceptions import NotFound
from .exceptions import ValidationError

# Regular expression to validate url-safe slugs for products
PRODUCT_SLUG_PATTERN = re.compile('^[a-z]+[-a-z0-9]*[a-z0-9]+$')

# Regular expression to validate url-safe slugs for editions/builds
PATH_SLUG_PATTERN = re.compile('^[a-zA-Z0-9-]+$')

# Regular expression for DM ticket branches (to auto-build slugs)
TICKET_BRANCH_PATTERN = re.compile('^tickets/(DM-[0-9]+)$')


def split_url(url, method='GET'):
    """Returns the endpoint name and arguments that match a given URL.

    This is the reverse of Flask's `url_for()`.
    """
    appctx = _app_ctx_stack.top
    reqctx = _request_ctx_stack.top
    if appctx is None:
        raise RuntimeError('Attempted to match a URL without the '
                           'application context being pushed. This has to be '
                           'executed when application context is available.')

    if reqctx is not None:
        url_adapter = reqctx.url_adapter
    else:
        url_adapter = appctx.url_adapter
        if url_adapter is None:
            raise RuntimeError('Application was not able to create a URL '
                               'adapter for request independent URL matching. '
                               'You might be able to fix this by setting '
                               'the SERVER_NAME config variable.')
    parsed_url = url_parse(url)
    if parsed_url.netloc is not '' and \
            parsed_url.netloc != url_adapter.server_name:
        raise ValidationError('Invalid URL: ' + url)
    try:
        result = url_adapter.match(parsed_url.path, method)
    except NotFound:
        raise ValidationError('Invalid URL: ' + url)
    return result


def validate_product_slug(slug):
    """Validate a URL-safe slug for products."""
    m = PRODUCT_SLUG_PATTERN.match(slug)
    if m is None or m.string != slug:
        raise ValidationError('Invalid slug: ' + slug)
    return True


def validate_path_slug(slug):
    """Validate a URL-safe slug for builds/editions. This validation
    is slightly more lax than validate_product_slug because build/edition
    slugs are only used in the paths, not as parts of domains."""
    m = PATH_SLUG_PATTERN.match(slug)
    if m is None or m.string != slug:
        raise ValidationError('Invalid slug: ' + slug)
    return True


def auto_slugify_edition(git_refs):
    """Given a list of Git refs, build a reasonable URL-safe slug."""
    slug = '-'.join(git_refs)

    # Customization for making slugs from DM ticket branches
    # Ideally we'd add a more formal API for adding similar behaviours
    m = TICKET_BRANCH_PATTERN.match(slug)
    if m is not None:
        return m.group(1)

    slug = slug.replace('/', '-')
    slug = slug.replace('_', '-')
    slug = slug.replace('.', '-')
    return slug


def format_utc_datetime(dt):
    """Standardized UTC `str` representation for a
    `datetime.datetime.Datetime`.
    """
    if dt is None:
        return None
    else:
        return dt.isoformat() + 'Z'


def parse_utc_datetime(datetime_str):
    """Parse a date string, returning a UTC datetime object."""
    if datetime_str is not None:
        date = datetime_parser.parse(datetime_str)\
            .astimezone(tzutc())\
            .replace(tzinfo=None)
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

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
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
    def coerce(cls, key, value):
        """Convert plain lists to MutableList."""
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, index, value):
        """Detect list set events and emit change events."""
        list.__setitem__(self, index, value)
        self.changed()

    def __delitem__(self, index):
        """Detect list del events and emit change events."""
        list.__delitem__(self, index)
        self.changed()
