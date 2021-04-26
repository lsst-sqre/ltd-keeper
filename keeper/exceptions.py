"""Custom exceptions."""

__all__ = [
    "ValidationError",
    "Route53Error",
    "S3Error",
    "FastlyError",
    "DasherError",
]


class ValidationError(ValueError):
    """Use a ValidationError whenever a API user provides bad input for PUT,
    POST, or PATCH requests.
    """


class Route53Error(Exception):
    """Errors related to Route 53 usage."""


class S3Error(Exception):
    """Errors related to AWS S3 usage."""


class FastlyError(Exception):
    """Errors related to Fastly API usage."""


class DasherError(Exception):
    """Errors related to LTD Dasher."""
