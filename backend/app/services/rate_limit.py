"""Process-local abuse protection for sensitive public endpoints."""

from __future__ import annotations

import time
import logging
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings

_requests: dict[str, deque[float]] = defaultdict(deque)
logger = logging.getLogger(__name__)


def _limit_for(request: Request) -> tuple[int, int] | None:
    path = request.url.path
    if request.method == "POST" and path == "/public/orders":
        return (10, 60)
    if request.method == "POST" and path == "/public/analytics":
        return (120, 60)
    if (
        request.method == "POST"
        and path.startswith("/public/orders/")
        and path.endswith("/feedback")
    ):
        return (10, 60)
    if request.method == "GET" and path.startswith("/public/orders/"):
        return (60, 60)
    if request.method == "POST" and path == "/auth/staff/login":
        return (10, 300)
    # Customer accounts. Signup and resend each cost a real SMS, so they are
    # capped hard; verify is capped to blunt code guessing from one address.
    if request.method == "POST" and path == "/auth/customer/signup":
        return (5, 3600)
    if request.method == "POST" and path == "/auth/customer/resend":
        return (5, 3600)
    if request.method == "POST" and path == "/auth/customer/verify":
        return (15, 900)
    if request.method == "POST" and path == "/auth/customer/login":
        return (10, 300)
    return None


async def rate_limit_sensitive_routes(request: Request, call_next):
    if not get_settings().rate_limit_enabled:
        return await call_next(request)
    limit = _limit_for(request)
    if not limit:
        return await call_next(request)

    max_requests, window_seconds = limit
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.method}:{request.url.path}"
    now = time.monotonic()
    bucket = _requests[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= max_requests:
        logger.warning(
            "Rate limit exceeded client=%s method=%s path=%s",
            client_host,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait and try again."},
            headers={"Retry-After": str(window_seconds)},
        )
    bucket.append(now)
    return await call_next(request)
