"""
Structured request logging middleware.

Emits one JSON log line per request with:
  request_id, method, path, status_code, duration_ms, driver_id, ride_id

driver_id is extracted from the JWT Bearer token payload without re-validation
(logging only — do not use for auth decisions).

ride_id is extracted from the URL path when present.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("halfapp.request")

# Matches ride_id in paths like /drivers/rides/123/..., /rides/456/cancel
_RIDE_ID_RE = re.compile(r"/rides?/(\d+)")

# Matches driver path prefix
_DRIVER_PATH_RE = re.compile(r"^/drivers/")


def _extract_ride_id(path: str) -> Optional[int]:
    m = _RIDE_ID_RE.search(path)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _extract_driver_id_from_bearer(authorization: Optional[str]) -> Optional[int]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1]
        # add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        uid = payload.get("user_id")
        return int(uid) if uid is not None else None
    except Exception:
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)
        path = request.url.path
        ride_id = _extract_ride_id(path)
        driver_id = _extract_driver_id_from_bearer(request.headers.get("authorization"))

        record = {
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        if driver_id is not None:
            record["driver_id"] = driver_id
        if ride_id is not None:
            record["ride_id"] = ride_id

        logger.info(json.dumps(record))

        response.headers["x-request-id"] = request_id
        return response
