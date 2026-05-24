"""Structured auth error payloads for JWT middleware (AUTH-001)."""

from __future__ import annotations

from typing import Any

AUTH_ERROR_UNAUTHENTICATED = "unauthenticated"
AUTH_ERROR_TOKEN_EXPIRED = "token_expired"
AUTH_ERROR_INVALID_TOKEN = "invalid_token"


def auth_error_detail(code: str, message: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": code}
    if message:
        payload["message"] = message
    return payload
