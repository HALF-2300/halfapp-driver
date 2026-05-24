"""In-memory auth rate limiting (SECURITY-001). Redis recommended for multi-instance later."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

_lock = threading.Lock()
_buckets: dict[str, list[float]] = defaultdict(list)

LOGIN_LIMIT = int(os.getenv("HALFAPP_AUTH_LOGIN_LIMIT", "10"))
LOGIN_WINDOW_SECONDS = 60
REGISTER_LIMIT = int(os.getenv("HALFAPP_AUTH_REGISTER_LIMIT", "10"))
REGISTER_WINDOW_SECONDS = 60
RESEND_LIMIT = int(os.getenv("HALFAPP_AUTH_RESEND_OTP_LIMIT", "3"))
RESEND_WINDOW_SECONDS = 3600


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _prune(timestamps: list[float], now: float, window: float) -> list[float]:
    cutoff = now - window
    return [t for t in timestamps if t > cutoff]


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds)."""
    now = time.time()
    bucket_key = f"{key}:{limit}:{window_seconds}"
    with _lock:
        hits = _prune(_buckets[bucket_key], now, window_seconds)
        if len(hits) >= limit:
            oldest = min(hits)
            retry_after = max(1, int(window_seconds - (now - oldest)) + 1)
            _buckets[bucket_key] = hits
            return False, retry_after
        hits.append(now)
        _buckets[bucket_key] = hits
        return True, 0


def too_many_requests_response(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "too_many_requests", "retry_after": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Protect auth endpoints from brute-force / registration abuse."""

    _RULES: dict[tuple[str, str], tuple[int, int]] = {
        ("POST", "/auth/login"): (LOGIN_LIMIT, LOGIN_WINDOW_SECONDS),
        ("POST", "/auth/register"): (REGISTER_LIMIT, REGISTER_WINDOW_SECONDS),
        ("POST", "/auth/verify"): (LOGIN_LIMIT, LOGIN_WINDOW_SECONDS),
        ("POST", "/auth/resend-otp"): (RESEND_LIMIT, RESEND_WINDOW_SECONDS),
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rule = self._RULES.get((request.method.upper(), request.url.path))
        if rule:
            limit, window = rule
            allowed, retry_after = check_rate_limit(
                f"{_client_key(request)}:{request.url.path}",
                limit=limit,
                window_seconds=window,
            )
            if not allowed:
                return too_many_requests_response(retry_after)
        return await call_next(request)


def reset_rate_limits_for_tests() -> None:
    with _lock:
        _buckets.clear()
