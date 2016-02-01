"""Custom ltd-keeper exceptions."""


class ValidationError(ValueError):
    """Use a ValidationError whenever a API user provides bad input for PUT,
    POST, or PATCH requests.
    """
    pass
