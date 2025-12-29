"""
Peptide AI - Clerk Backend API Utilities

Functions for looking up user information from Clerk.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded Clerk client
_clerk_client = None


def get_clerk_client():
    """Get or create Clerk client instance."""
    global _clerk_client

    if _clerk_client is not None:
        return _clerk_client

    secret_key = os.getenv("CLERK_SECRET_KEY")
    if not secret_key:
        logger.warning("CLERK_SECRET_KEY not set - user lookups will fail")
        return None

    try:
        from clerk_backend_api import Clerk
        _clerk_client = Clerk(bearer_auth=secret_key)
        return _clerk_client
    except ImportError:
        logger.error("clerk-backend-api not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Clerk client: {e}")
        return None


def get_user_email(user_id: str) -> Optional[str]:
    """
    Look up a user's primary email address from Clerk.

    Args:
        user_id: The Clerk user ID (e.g., "user_2abc123...")

    Returns:
        The user's primary email address, or None if not found
    """
    if not user_id or user_id == "anonymous":
        return None

    client = get_clerk_client()
    if not client:
        return None

    try:
        user = client.users.get(user_id=user_id)

        if user and user.email_addresses:
            # Find primary email or use first one
            for email in user.email_addresses:
                if hasattr(email, 'id') and user.primary_email_address_id == email.id:
                    return email.email_address
            # Fallback to first email
            return user.email_addresses[0].email_address

        return None
    except Exception as e:
        logger.error(f"Failed to get user email for {user_id}: {e}")
        return None


def get_user_info(user_id: str) -> Optional[dict]:
    """
    Look up user information from Clerk.

    Args:
        user_id: The Clerk user ID

    Returns:
        Dict with user info (email, first_name, last_name) or None
    """
    if not user_id or user_id == "anonymous":
        return None

    client = get_clerk_client()
    if not client:
        return None

    try:
        user = client.users.get(user_id=user_id)

        if not user:
            return None

        email = None
        if user.email_addresses:
            for e in user.email_addresses:
                if hasattr(e, 'id') and user.primary_email_address_id == e.id:
                    email = e.email_address
                    break
            if not email:
                email = user.email_addresses[0].email_address

        return {
            "email": email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
        }
    except Exception as e:
        logger.error(f"Failed to get user info for {user_id}: {e}")
        return None
