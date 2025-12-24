"""
Peptide AI - Authentication Middleware

API key and JWT validation for securing endpoints.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import hashlib
from typing import Optional
import logging

from api.deps import get_settings, get_database

logger = logging.getLogger(__name__)


def cors_response(status_code: int, content: dict) -> JSONResponse:
    """Create a JSONResponse with CORS headers for error responses."""
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication

    Supports:
    - API key in header (X-API-Key)
    - API key in query param (?api_key=...)
    - Public endpoints (no auth required)
    """

    # Endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/health/ready",
        "/health/live",
        "/health/config",
    }

    # Path prefixes that don't require authentication
    PUBLIC_PREFIXES = [
        "/api/v1/share/",  # Public shared conversation viewing
    ]

    # Endpoints that work with or without authentication
    # (user will be None if no auth provided)
    OPTIONAL_AUTH_PATHS = {
        "/api/v1/analytics/track",
        "/api/v1/analytics/affiliate/click",
        "/api/v1/feedback",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for public path prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract API key
        api_key = self._extract_api_key(request)

        # For optional auth paths, proceed without auth if no key
        if not api_key and request.url.path in self.OPTIONAL_AUTH_PATHS:
            # Set empty user state so get_optional_user returns None
            request.state.user_id = None
            request.state.subscription_tier = None
            request.state.is_admin = False
            return await call_next(request)

        if not api_key:
            return cors_response(
                status_code=401,
                content={
                    "error": "API key required",
                    "type": "authentication_error",
                    "detail": "Provide API key via X-API-Key header or api_key query parameter"
                }
            )

        # Validate API key
        user_info = await self._validate_api_key(api_key, request)

        if not user_info:
            return cors_response(
                status_code=401,
                content={
                    "error": "Invalid API key",
                    "type": "authentication_error"
                }
            )

        # Attach user info to request state
        request.state.user_id = user_info.get("user_id")
        request.state.subscription_tier = user_info.get("subscription_tier", "free")
        request.state.is_admin = user_info.get("is_admin", False)

        return await call_next(request)

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request"""
        # Try header first
        api_key = request.headers.get(self.settings.api_key_header)
        if api_key:
            return api_key

        # Try query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None

    async def _validate_api_key(self, api_key: str, request: Request) -> Optional[dict]:
        """
        Validate API key and return user info

        Returns dict with: user_id, subscription_tier, is_admin
        """
        # Check master key (for dev/admin or frontend proxy)
        if api_key == self.settings.master_api_key:
            # Check for Clerk user ID header (from frontend proxy)
            # This allows per-user isolation when using master key
            clerk_user_id = request.headers.get("X-Clerk-User-Id")
            if clerk_user_id:
                return {
                    "user_id": clerk_user_id,
                    "subscription_tier": "free",
                    "is_admin": False
                }
            # No Clerk ID - use admin (for direct API access)
            return {
                "user_id": "admin",
                "subscription_tier": "admin",
                "is_admin": True
            }

        # Hash the key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            db = get_database()
            key_doc = await db.api_keys.find_one({"key_hash": key_hash})

            if not key_doc:
                return None

            if not key_doc.get("is_active", True):
                return None

            # Get user info
            user = await db.users.find_one({"user_id": key_doc["user_id"]})

            return {
                "user_id": key_doc["user_id"],
                "subscription_tier": user.get("subscription_tier", "free") if user else "free",
                "is_admin": key_doc.get("is_admin", False)
            }

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency to get current user from request state

    Use in routes:
        @router.get("/me")
        async def get_me(user: dict = Depends(get_current_user)):
            return user
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user_id": request.state.user_id,
        "subscription_tier": request.state.subscription_tier,
        "is_admin": request.state.is_admin
    }


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency to get current user if authenticated, or None if not.

    Use for endpoints that work for both authenticated and anonymous users.

    Use in routes:
        @router.post("/track")
        async def track_event(user: Optional[dict] = Depends(get_optional_user)):
            user_id = user["user_id"] if user else None
    """
    if not hasattr(request.state, "user_id") or request.state.user_id is None:
        return None

    return {
        "user_id": request.state.user_id,
        "subscription_tier": request.state.subscription_tier,
        "is_admin": request.state.is_admin
    }


async def require_tier(request: Request, required_tiers: list[str]) -> bool:
    """
    Check if user has required subscription tier

    Use in routes:
        @router.get("/premium")
        async def premium_feature(request: Request):
            if not await require_tier(request, ["pro", "pro_ship", "creator", "admin"]):
                raise HTTPException(403, "Upgrade required")
    """
    tier = getattr(request.state, "subscription_tier", "free")
    return tier in required_tiers


def create_api_key(user_id: str) -> tuple[str, str]:
    """
    Create a new API key for a user

    Returns: (raw_key, key_hash)
    - raw_key: Give this to the user (only shown once)
    - key_hash: Store this in the database
    """
    import secrets
    raw_key = f"pk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash
