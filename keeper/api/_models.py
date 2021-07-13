"""Pydantic Models for the v1 API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, SecretStr


class AuthTokenResponse(BaseModel):
    """The auth token resource."""

    token: SecretStr
    """Token string. Use this token in the basic auth "username" field."""

    class Config:
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None,
        }
