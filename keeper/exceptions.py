"""Custom ltd-keeper exceptions."""


class ValidationError(ValueError):
    """Use a ValidationError whenever a API user provides bad input for PUT,
    POST, or PATCH requests.
    """

    pass


class Route53Error(Exception):
    """Errors related to Route 53 usage."""

    pass


class S3Error(Exception):
    """Errors related to AWS S3 usage."""

    pass


class FastlyError(Exception):
    """"Errors related to Fastly API usage."""

    pass


class DasherError(Exception):
    """Errors related to LTD Dasher."""

    pass
