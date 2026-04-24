"""
PathForge API — OAuth Routes
================================
Social login endpoints for Google and Microsoft OAuth providers.

Sprint 39: Phase E — Google + Microsoft OAuth / Social Login.
Tier-1 Audit: F2 (JWKS), F9 (google-auth), F10 (msal cleanup),
              F11/F12 (asyncio.to_thread), F14 (Literal), F16 (auto-verify).

Flow:
1. Frontend obtains an ID token via Google Sign-In SDK or MSAL.js
2. Frontend sends the ID token to POST /auth/oauth/{provider}
3. Backend verifies the token with the provider (JWKS for Microsoft,
   google-auth for Google) — both run in thread pool to avoid blocking
4. Backend creates or retrieves the user, auto-verified
5. Backend returns access + refresh JWT tokens
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token
from app.schemas.user import TokenResponse
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])

# ── Types ──────────────────────────────────────────────────────

OAuthProvider = Literal["google", "microsoft"]


# ── Request Schema ─────────────────────────────────────────────


class OAuthTokenRequest(BaseModel):
    """ID token received from frontend OAuth SDK."""
    id_token: str = Field(min_length=1, description="ID token from OAuth provider")


# ── Microsoft JWKS Client (cached, lazy-initialized) ──────────

_MICROSOFT_JWKS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
_ms_jwks_client: PyJWKClient | None = None


def _get_ms_jwks_client() -> PyJWKClient:
    """Lazily create a cached JWKS client for Microsoft token verification.

    Keys are cached for 1 hour to avoid redundant HTTP calls.
    The client is a module-level singleton for efficiency.
    """
    global _ms_jwks_client
    if _ms_jwks_client is None:
        _ms_jwks_client = PyJWKClient(
            _MICROSOFT_JWKS_URL,
            cache_keys=True,
            lifespan=3600,
        )
    return _ms_jwks_client


# ── Token Verification ─────────────────────────────────────────


async def _verify_google_token(id_token: str) -> dict[str, str]:
    """Verify a Google ID token and return user info.

    Uses google-auth library for OIDC token verification.
    The verification call is synchronous (uses ``requests`` internally),
    so we run it in a thread pool to avoid blocking the event loop (F12).

    Returns:
        Dict with 'email', 'name', and 'sub' (Google user ID).

    Raises:
        HTTPException: If token verification fails.
    """
    if not settings.google_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured",
        )

    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token as google_id_token

        # F12: google.oauth2.id_token.verify_oauth2_token uses synchronous HTTP
        # via the `requests` library — must run in thread pool
        claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            id_token,
            GoogleRequest(),
            settings.google_oauth_client_id,
        )

        email = claims.get("email")
        name = claims.get("name", "")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token does not contain an email address",
            )

        return {"email": email, "name": name, "sub": claims.get("sub", "")}

    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc


async def _verify_microsoft_token(id_token: str) -> dict[str, str]:
    """Verify a Microsoft ID token using JWKS and return user info.

    Uses PyJWT's PyJWKClient to fetch Microsoft's public signing keys
    and verify the RS256 signature. The JWKS HTTP call is synchronous,
    so we run it in a thread pool to avoid blocking the event loop (F11).

    Returns:
        Dict with 'email', 'name', and 'sub' (Microsoft user ID).

    Raises:
        HTTPException: If token verification fails.
    """
    if not settings.microsoft_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Microsoft OAuth is not configured",
        )

    try:
        jwks_client = _get_ms_jwks_client()

        # F11: PyJWKClient.get_signing_key_from_jwt() is synchronous HTTP
        # — must run in thread pool to avoid blocking the event loop
        signing_key = await asyncio.to_thread(
            jwks_client.get_signing_key_from_jwt, id_token
        )

        claims = pyjwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.microsoft_oauth_client_id,
            options={"verify_exp": True},
        )

        email = claims.get("email") or claims.get("preferred_username")
        name = claims.get("name", "")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Microsoft token does not contain an email address",
            )

        return {"email": email, "name": name, "sub": claims.get("sub", "")}

    except pyjwt.ExpiredSignatureError as exc:
        logger.warning("Microsoft token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft token has expired",
        ) from exc
    except pyjwt.InvalidTokenError as exc:
        logger.warning("Microsoft token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Microsoft ID token",
        ) from exc

# ── OAuth Endpoints ────────────────────────────────────────────


@router.post(
    "/{provider}",
    response_model=TokenResponse,
    summary="Authenticate via OAuth provider (Google or Microsoft)",
)
@limiter.limit(settings.rate_limit_login)
async def oauth_login(
    request: Request,
    provider: OAuthProvider,
    payload: OAuthTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange an OAuth provider ID token for PathForge JWT tokens.

    Supported providers: google, microsoft (F14: enforced via Literal type).
    If the user doesn't exist, they are auto-created with is_verified=True.
    If the user exists, account linking is attempted (F16: auto-verify).
    """
    # F14: FastAPI auto-validates provider via Literal type — no manual check needed
    verifier = _verify_google_token if provider == "google" else _verify_microsoft_token

    # Verify the ID token with the provider
    user_info = await verifier(payload.id_token)
    email = user_info["email"]
    name = user_info["name"]

    # Check if user already exists
    user = await UserService.get_by_email(db, email)

    if user:
        # Account linking — if user exists but with different provider,
        # allow login since email is verified by the OAuth provider.
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        # ── Verification cross-provider policy (F16) ───────────────
        #
        # If a user initially registered with email+password but never
        # clicked the verification link, then later signs in via
        # Google/Microsoft OAuth, the OAuth provider has already
        # verified the email address by issuing an ID token for it.
        # We therefore mark the account as verified here.
        #
        # Security note (Sprint 39 audit F31): this is intentional
        # and NOT a verification bypass. The email-based login flow
        # (``UserService.authenticate``) still enforces
        # ``is_verified == True`` independently — an attacker who
        # knew the victim's password but did not control the email
        # cannot use this path because they cannot complete the
        # Google/Microsoft OAuth challenge for that address. In
        # other words, trust is transitively passed from "OAuth
        # provider asserts control of the inbox" → "inbox owner is
        # verified", which matches exactly what the email
        # verification link would have proved.
        if not user.is_verified:
            user.is_verified = True
            await db.flush()
    else:
        # Create new OAuth user (no password, auto-verified)
        user = await UserService.create_user(
            db,
            email=email,
            full_name=name or email.split("@")[0],
            auth_provider=provider,
            is_verified=True,
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
