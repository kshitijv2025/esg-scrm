"""Rate limiting middleware using in-memory store (Redis-backed when available)."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sliding-window rate limiter
# ---------------------------------------------------------------------------


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter with optional Redis backend."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        redis_url: Optional[str] = None,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis_url = redis_url
        self._redis: Optional[object] = None
        self._local_store: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._use_redis = bool(redis_url)
        if self._use_redis:
            self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            logger.info("rate_limit.redis_connected url=%s", self._redis_url)
        except Exception as exc:
            logger.warning("rate_limit.redis_init_failed error=%s — falling back to in-memory", exc)
            self._redis = None
            self._use_redis = False

    async def is_allowed(self, key: str) -> tuple[bool, dict[str, int]]:
        """Check if request is allowed. Returns (allowed, info)."""
        now = time.time()
        window_start = now - self.window_seconds

        if self._use_redis and self._redis:
            return await self._redis_is_allowed(key, now, window_start)
        return await self._local_is_allowed(key, now, window_start)

    async def _local_is_allowed(
        self, key: str, now: float, window_start: float
    ) -> tuple[bool, dict[str, int]]:
        async with self._lock:
            timestamps = self._local_store[key]
            # Prune old entries
            timestamps[:] = [t for t in timestamps if t > window_start]
            remaining = max(0, self.max_requests - len(timestamps))
            if timestamps and len(timestamps) >= self.max_requests:
                oldest = min(timestamps)
                retry_after = int(oldest + self.window_seconds - now) + 1
                return False, {
                    "remaining": 0,
                    "limit": self.max_requests,
                    "retry_after": retry_after,
                }
            timestamps.append(now)
            return True, {"remaining": remaining - 1, "limit": self.max_requests}

    async def _redis_is_allowed(
        self, key: str, now: float, window_start: float
    ) -> tuple[bool, dict[str, int]]:
        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window_seconds + 1)
            results = await pipe.execute()
            count = results[1]
            remaining = max(0, self.max_requests - count)
            if count >= self.max_requests:
                oldest = await self._redis.zrange(key, 0, 0, withscores=True)
                retry_after = (
                    int(oldest[0][1] + self.window_seconds - now) + 1
                    if oldest
                    else self.window_seconds
                )
                return False, {
                    "remaining": 0,
                    "limit": self.max_requests,
                    "retry_after": retry_after,
                }
            return True, {"remaining": remaining, "limit": self.max_requests}
        except Exception as exc:
            logger.warning("rate_limit.redis_error error=%s — falling back to local", exc)
            self._use_redis = False
            self._redis = None
            return await self._local_is_allowed(key, now, window_start)


# ---------------------------------------------------------------------------
# Rate limit configurations per route group
# ---------------------------------------------------------------------------

RATE_LIMITS: dict[str, tuple[int, int]] = {
    # path_prefix -> (max_requests, window_seconds)
    "/api/whatsapp/webhook": (100, 60),  # 100 req/min per IP
    "/api/upload": (10, 3600),  # 10 req/hour per user (CSV uploads)
    "/api/alerts": (60, 60),
    "/api/audit": (60, 60),
    "/api/dashboard": (300, 60),
    "/api/evidence": (300, 60),
    "/api/emission-factors": (300, 60),
    "/api/frameworks": (300, 60),
    "/api/questionnaires": (300, 60),
    "/api/reports": (300, 60),
    "/api/risk": (300, 60),
    "/api/scope3": (300, 60),
    "/api/suppliers": (300, 60),
    "/api/templates": (300, 60),
    "/api/trust": (300, 60),
    "/api/admin": (60, 60),
    "/api/ml": (60, 60),
    "/api/water": (60, 60),
    "/api/auth/login": (20, 60),  # Login attempts
    "/api/auth/register": (10, 3600),  # Registration
}


def _get_rate_limit_key(request: Request, max_requests: int, window_seconds: int) -> str:
    """Derive a rate limit key from request."""
    # Prefer user_id from JWT, fall back to IP
    user = getattr(request.state, "user", None)
    if user and user.get("sub"):
        return f"user:{user['sub']}"
    # Fall back to IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        client_ip = forwarded
    return f"ip:{client_ip}"


def _match_route(path: str) -> Optional[tuple[int, int]]:
    """Match request path to a rate limit config."""
    for prefix, limits in sorted(RATE_LIMITS.items(), key=lambda x: -len(x[0])):
        if path.startswith(prefix):
            return limits
    return None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-user/IP rate limits."""

    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self._redis_url = redis_url or os.environ.get("REDIS_URL")
        self._limiters: dict[str, SlidingWindowRateLimiter] = {}
        self._lock = asyncio.Lock()

    async def _get_limiter(
        self, prefix: str, max_req: int, window: int
    ) -> SlidingWindowRateLimiter:
        if prefix not in self._limiters:
            async with self._lock:
                if prefix not in self._limiters:
                    self._limiters[prefix] = SlidingWindowRateLimiter(
                        max_requests=max_req,
                        window_seconds=window,
                        redis_url=self._redis_url,
                    )
        return self._limiters[prefix]

    def reset_state(self) -> None:
        """Clear all rate limiter state. For use in tests only."""
        self._limiters.clear()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        limits = _match_route(path)

        if limits is None:
            return await call_next(request)

        max_requests, window_seconds = limits
        limiter = await self._get_limiter(path, max_requests, window_seconds)
        rate_key = _get_rate_limit_key(request, max_requests, window_seconds)

        allowed, info = await limiter.is_allowed(rate_key)

        if not allowed:
            retry_after = info.get("retry_after", window_seconds)
            logger.warning(
                "rate_limit.exceeded key=%s path=%s limit=%d",
                rate_key,
                path,
                max_requests,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after} seconds."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        return response
