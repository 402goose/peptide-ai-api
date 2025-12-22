"""
Peptide AI - Rate Limiting Middleware

Token bucket rate limiting with tier-based limits.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime, timedelta
import logging
from typing import Optional

from api.deps import get_settings, get_database

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with subscription tier support

    Uses token bucket algorithm:
    - Each user gets a bucket of tokens
    - Tokens refill over time
    - Each request costs 1 token
    - Different tiers have different bucket sizes
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/health/ready",
        "/health/live",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip for OPTIONS
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get rate limit key (user_id if authenticated, IP otherwise)
        rate_key = self._get_rate_key(request)

        # Get tier limit
        tier = getattr(request.state, "subscription_tier", "free")
        limit = self.settings.tier_limits.get(tier, 10)

        # Check rate limit
        allowed, remaining, reset_at = await self._check_rate_limit(rate_key, limit)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "limit": limit,
                    "remaining": 0,
                    "reset_at": reset_at.isoformat() if reset_at else None,
                    "upgrade_hint": "Upgrade your subscription for higher limits" if tier == "free" else None
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at.timestamp())) if reset_at else "",
                    "Retry-After": str(60)  # seconds
                }
            )

        # Process request and add rate limit headers
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if reset_at:
            response.headers["X-RateLimit-Reset"] = str(int(reset_at.timestamp()))

        return response

    def _get_rate_key(self, request: Request) -> str:
        """Get key for rate limiting - user_id or IP"""
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(
        self,
        key: str,
        limit: int
    ) -> tuple[bool, int, Optional[datetime]]:
        """
        Check if request is within rate limit

        Returns: (allowed, remaining, reset_at)
        """
        try:
            db = get_database()
            window = timedelta(seconds=60)  # 1 minute window
            now = datetime.utcnow()

            # Get or create rate limit record
            record = await db.rate_limits.find_one({"key": key})

            if not record:
                # First request - create record
                await db.rate_limits.insert_one({
                    "key": key,
                    "count": 1,
                    "window_start": now,
                    "expires_at": now + window
                })
                return True, limit - 1, now + window

            # Check if window has expired
            window_start = record.get("window_start", now)
            if now - window_start > window:
                # Reset window
                await db.rate_limits.update_one(
                    {"key": key},
                    {
                        "$set": {
                            "count": 1,
                            "window_start": now,
                            "expires_at": now + window
                        }
                    }
                )
                return True, limit - 1, now + window

            # Check count
            current_count = record.get("count", 0)

            if current_count >= limit:
                # Over limit
                reset_at = window_start + window
                return False, 0, reset_at

            # Increment and allow
            await db.rate_limits.update_one(
                {"key": key},
                {"$inc": {"count": 1}}
            )

            remaining = limit - current_count - 1
            reset_at = window_start + window
            return True, remaining, reset_at

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return True, limit, None


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, limit: int, reset_at: datetime):
        self.limit = limit
        self.reset_at = reset_at
        super().__init__(f"Rate limit of {limit} requests exceeded")
