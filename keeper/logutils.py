"""Logging helpers and utilities."""

import uuid
from functools import wraps
from timeit import default_timer as timer
from typing import Any, Callable, TypeVar

import structlog
from flask import make_response, request

__all__ = ["log_route"]

F = TypeVar("F", bound=Callable[..., Any])


def log_route() -> Callable[[F], F]:
    """Route decorator to initialize a thread-local logger for a route.
    """

    def decorator(f):  # type: ignore
        @wraps(f)
        def decorated_function(*args, **kwargs):  # type: ignore
            # Initialize a timer to capture the response time
            # This is for convenience, in addition to route monitoring.
            start_time = timer()

            # Initialize a new thread-local logger and add a unique request
            # ID to its context.
            # http://www.structlog.org/en/stable/examples.html
            logger = structlog.get_logger()
            log = logger.new(
                request_id=str(uuid.uuid4()),
                path=request.path,
                method=request.method,
            )

            # Pass through route
            response = f(*args, **kwargs)
            response = make_response(response)

            # Close out the logger
            end_time = timer()
            log.info(
                status=response.status_code,
                response_time=end_time - start_time,
            )

            return response

        return decorated_function

    return decorator
