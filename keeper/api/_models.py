"""Pydantic Models for the v1 API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, HttpUrl, SecretStr


class AuthTokenResponse(BaseModel):
    """The auth token resource."""

    token: SecretStr
    """Token string. Use this token in the basic auth "username" field."""

    class Config:
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None,
        }


class RootLinks(BaseModel):
    """Sub-resource containing links to APIs."""

    self: HttpUrl
    """The URL of this resource."""

    token: HttpUrl
    """The URL of the authorization endpoint to obtain a token."""

    products: HttpUrl
    """The endpoint for the products listing."""


class RootData(BaseModel):
    """Sub-resource providing metadata about the service."""

    server_version: str
    """The service vesion."""

    documentation: HttpUrl
    """The URL of the service's documentation."""

    message: str
    """Description of the service."""


class RootResponse(BaseModel):
    """The root endpoint resources provides metadata and links for the
    service.
    """

    data: RootData

    links: RootLinks
