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
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
)
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


async def _verify_google_token(id_token: str) -> dict[str, str | bool]:
    """Verify a Google ID token and return user info.

    Uses google-auth library for OIDC token verification.
    ``verify_oauth2_token`` validates issuer (accounts.google.com),
    audience (our client_id), and signature in one call. The call is
    synchronous (uses ``requests`` internally) so we run it in a
    thread pool to avoid blocking the event loop (F12).

    Returns:
        Dict with ``email``, ``name``, ``sub`` (Google user ID),
        and ``email_verified`` (bool — Google sets this to True for
        Workspace accounts and verified consumer accounts; we surface
        it so the route handler can gate cross-provider linking).

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

        # S-H2: Google asserts ``email_verified=true`` only when it has
        # confirmed the address (Workspace SSO, or a consumer account
        # that completed verification). Pass-through for the gate.
        email_verified = bool(claims.get("email_verified", False))

        return {
            "email": email,
            "name": name,
            "sub": claims.get("sub", ""),
            "email_verified": email_verified,
        }

    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc


async def _verify_microsoft_token(id_token: str) -> dict[str, str | bool]:
    """Verify a Microsoft ID token using JWKS and return user info.

    Uses PyJWT's PyJWKClient to fetch Microsoft's public signing keys
    and verify the RS256 signature. The JWKS HTTP call is synchronous,
    so we run it in a thread pool to avoid blocking the event loop (F11).

    Sprint 39 audit S-H1 — tenant + issuer validation:
        ``/common/discovery/v2.0/keys`` serves keys for *every* Azure
        AD tenant (and for personal Microsoft accounts via
        ``9188040d-6c67-4c5b-b112-36a304b66dad``). Verifying only the
        signature + audience lets any tenant whose admin obtains our
        client_id mint tokens that pass our checks. This function now:
            (a) decodes the unverified header to extract ``tid``;
            (b) refuses the token if ``tid`` is not in the
                ``microsoft_oauth_allowed_tenants`` allowlist;
            (c) re-decodes with explicit ``issuer=``-binding to the
                tenant-specific URL so the signed claim must match.
        Empty allowlist ⇒ reject every Microsoft token (operator
        must opt in by listing tenant IDs).

    Sprint 39 audit S-H2 — ``email_verified`` gate:
        Personal MSA tokens may carry a self-asserted ``email``
        claim. Cross-provider account linking only trusts the
        provider's email assertion when ``email_verified == True``
        — that contract belongs in the verifier so the route handler
        cannot accidentally bypass it. Returned dict carries an
        explicit ``email_verified`` boolean.

    Returns:
        Dict with ``email``, ``name``, ``sub`` (subject claim),
        and ``email_verified`` (bool).

    Raises:
        HTTPException: If token verification fails.
    """
    if not settings.microsoft_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Microsoft OAuth is not configured",
        )

    allowed_tenants = settings.microsoft_oauth_allowed_tenants
    if not allowed_tenants:
        # Tenant allowlist is empty — explicit operator opt-in required.
        # Surface 501 (rather than 401) so the caller knows the
        # endpoint is reachable but configuration is incomplete.
        logger.warning(
            "Microsoft OAuth: client_id is set but allowlist is empty — "
            "rejecting; set MICROSOFT_OAUTH_ALLOWED_TENANTS to opt in."
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Microsoft OAuth tenant allowlist is not configured",
        )

    try:
        # First pass: read the unverified ``tid`` claim to pick the
        # tenant-specific issuer. ``options={"verify_signature": False}``
        # is safe here because we re-verify the signature below — this
        # decode is purely to learn which issuer string to bind.
        unverified = pyjwt.decode(
            id_token,
            options={"verify_signature": False},
        )
        tenant_id = unverified.get("tid")
        if not tenant_id or tenant_id not in allowed_tenants:
            logger.warning(
                "Microsoft OAuth: tenant %r not in allowlist",
                tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Microsoft tenant is not authorised for this application",
            )

        jwks_client = _get_ms_jwks_client()

        # F11: PyJWKClient.get_signing_key_from_jwt() is synchronous HTTP
        # — must run in thread pool to avoid blocking the event loop
        signing_key = await asyncio.to_thread(jwks_client.get_signing_key_from_jwt, id_token)

        expected_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        claims = pyjwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.microsoft_oauth_client_id,
            issuer=expected_issuer,
            options={"verify_exp": True, "verify_iss": True},
        )

        email = claims.get("email") or claims.get("preferred_username")
        name = claims.get("name", "")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Microsoft token does not contain an email address",
            )

        # S-H2: surface the verifier's belief about email ownership
        # so the route handler can branch on it.
        email_verified = bool(claims.get("email_verified", False))

        return {
            "email": email,
            "name": name,
            "sub": claims.get("sub", ""),
            "email_verified": email_verified,
        }

    except pyjwt.ExpiredSignatureError as exc:
        logger.warning("Microsoft token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft token has expired",
        ) from exc
    except pyjwt.InvalidIssuerError as exc:
        logger.warning("Microsoft token issuer mismatch: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft token issuer is not trusted",
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
@route_query_budget(max_queries=6)
async def oauth_login(
    request: Request,
    response: Response,
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
    email = str(user_info["email"])
    name = str(user_info["name"])
    # Sprint 39 audit S-H2: only the provider's signed
    # ``email_verified`` claim authorises us to bind this email to an
    # existing account or to auto-verify a brand-new one. Without it
    # the address is self-asserted (typical of Microsoft personal
    # accounts) and we treat the OAuth login as anonymous-equivalent.
    email_verified = bool(user_info.get("email_verified", False))

    # Check if user already exists
    user = await UserService.get_by_email(db, email)

    if user:
        # Account linking guards.
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # ── Verification cross-provider policy (F16 + S-H2) ────────
        #
        # If a user initially registered with email+password but
        # never clicked the verification link, then later signs in
        # via Google/Microsoft OAuth, the OAuth provider's signed
        # ``email_verified`` claim is treated as equivalent to the
        # verification link — but ONLY when the claim is present and
        # true. A self-asserted email from a personal Microsoft
        # account (``email_verified`` absent or false) does NOT
        # complete the gate; we surface 403 so the user is told to
        # complete email verification by the original channel.
        #
        # Security note: even with this guard, the email-based login
        # flow (``UserService.authenticate``) still enforces
        # ``is_verified == True`` independently — defence in depth.
        if not user.is_verified:
            if not email_verified:
                logger.warning(
                    "OAuth account-linking blocked: provider=%s did not assert "
                    "email_verified for existing unverified account",
                    provider,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Your provider did not confirm this email is verified. "
                        "Please complete email verification with the link we "
                        "sent during registration before signing in via "
                        f"{provider}."
                    ),
                )
            user.is_verified = True
            await db.flush()
    else:
        # New OAuth user. We require ``email_verified`` here too —
        # otherwise an attacker can claim any email by signing into a
        # personal Microsoft account that advertises it.
        if not email_verified:
            logger.warning(
                "OAuth user creation blocked: provider=%s did not assert email_verified",
                provider,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"{provider.title()} did not confirm this email address "
                    "is verified. Please use a verified account or sign up "
                    "with email + password."
                ),
            )

        user = await UserService.create_user(
            db,
            email=email,
            full_name=name or email.split("@")[0],
            auth_provider=provider,
            is_verified=True,
        )

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    # Track 1 / ADR-0006: OAuth login also sets the cookie pair so the
    # post-OAuth web flow can switch transparently.
    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return tokens
