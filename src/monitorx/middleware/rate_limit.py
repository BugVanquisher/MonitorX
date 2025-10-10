"""Rate limiting middleware for MonitorX API."""
import os
import time
from typing import Dict, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60
    ):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        # Store: {client_id: [(timestamp, request_count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Cleanup every 5 minutes

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory growth."""
        now = time.time()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        cutoff = now - self.window_seconds
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                (ts, count) for ts, count in self.requests[client_id]
                if ts > cutoff
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]

        self.last_cleanup = now
        logger.debug(f"Rate limiter cleanup completed. Active clients: {len(self.requests)}")

    def is_allowed(self, client_id: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        self._cleanup_old_entries()

        now = time.time()
        window_start = now - self.window_seconds

        # Get requests in current window
        current_requests = [
            (ts, count) for ts, count in self.requests[client_id]
            if ts > window_start
        ]

        # Calculate total requests in window
        total_requests = sum(count for _, count in current_requests)

        # Rate limit info for headers
        info = {
            "limit": self.requests_per_window,
            "remaining": max(0, self.requests_per_window - total_requests),
            "reset": int(window_start + self.window_seconds)
        }

        if total_requests >= self.requests_per_window:
            return False, info

        # Add current request
        self.requests[client_id].append((now, 1))

        # Keep only recent entries
        self.requests[client_id] = [
            (ts, count) for ts, count in self.requests[client_id]
            if ts > window_start
        ]

        return True, info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Limits requests per client based on IP address or API key.
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)

        # Load config from environment
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
        self.requests_per_minute = int(
            os.getenv("RATE_LIMIT_REQUESTS", str(requests_per_minute))
        )
        self.window_seconds = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

        self.limiter = RateLimiter(
            requests_per_window=self.requests_per_minute,
            window_seconds=self.window_seconds
        )

        # Paths to exclude from rate limiting
        self.excluded_paths = {"/docs", "/redoc", "/openapi.json", "/", "/api/v1/health"}

        logger.info(
            f"Rate limiting {'enabled' if self.enabled else 'disabled'}: "
            f"{self.requests_per_minute} requests per {self.window_seconds}s"
        )

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier (API key or IP)."""
        # Prefer API key if present
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key[:16]}"  # Use first 16 chars

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip if disabled or excluded path
        if not self.enabled or request.url.path in self.excluded_paths:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        allowed, info = self.limiter.is_allowed(client_id)

        # Add rate limit headers
        response_headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"])
        }

        if not allowed:
            logger.warning(f"Rate limit exceeded for client: {client_id}")

            # Calculate retry after
            retry_after = info["reset"] - int(time.time())

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": info["limit"],
                    "window": f"{self.window_seconds}s",
                    "retry_after": retry_after
                },
                headers={
                    **response_headers,
                    "Retry-After": str(retry_after)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for header, value in response_headers.items():
            response.headers[header] = value

        return response


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter (alternative implementation).

    More sophisticated than sliding window, allows bursts.
    """

    def __init__(
        self,
        rate: float = 100.0,  # tokens per second
        capacity: int = 100  # bucket capacity
    ):
        self.rate = rate
        self.capacity = capacity
        # Store: {client_id: (tokens, last_update)}
        self.buckets: Dict[str, Tuple[float, float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed using token bucket algorithm."""
        now = time.time()

        if client_id not in self.buckets:
            # New client, start with full bucket
            self.buckets[client_id] = (self.capacity - 1, now)
            return True

        tokens, last_update = self.buckets[client_id]

        # Add tokens based on elapsed time
        elapsed = now - last_update
        tokens = min(self.capacity, tokens + (elapsed * self.rate))

        if tokens >= 1:
            # Consume one token
            self.buckets[client_id] = (tokens - 1, now)
            return True
        else:
            # No tokens available
            self.buckets[client_id] = (tokens, now)
            return False
