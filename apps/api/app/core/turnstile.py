"""
PathForge — Cloudflare Turnstile CAPTCHA Verification
========================================================
Server-side token validation for Turnstile CAPTCHA.

When `turnstile_secret_key` is empty (development), verification is skipped.
In production, all protected endpoints require a valid Turnstile token.

Sprint 39: Initial implementation for registration endpoint.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str | None) -> bool:
    """Verify a Turnstile CAPTCHA token with Cloudflare.

    Args:
        token: The Turnstile response token from the frontend widget.

    Returns:
        True if verification succeeds or is skipped (dev mode).

    Raises:
        HTTPException: If verification fails in production.
    """
    # Skip verification in development (no secret key configured)
    if not settings.turnstile_secret_key:
        logger.debug("Turnstile verification skipped (no secret key configured)")
        return True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification is required",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.turnstile_secret_key,
                    "response": token,
                },
            )
            result = response.json()

        if not result.get("success", False):
            error_codes = result.get("error-codes", [])
            logger.warning(
                "Turnstile verification failed: %s",
                ", ".join(error_codes),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPTCHA verification failed. Please try again.",
            )

        return True

    except httpx.HTTPError as exc:
        logger.exception("Turnstile API request failed")
        # In production, fail closed (reject if we can't verify)
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="CAPTCHA service temporarily unavailable",
            ) from exc
        # In development, fail open
        return True
