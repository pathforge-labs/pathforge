"""
PathForge API — CSRF Protection (Track 1 / ADR-0006)
=====================================================
Double-submit cookie CSRF protection for the cookie auth path.

Background
----------
With auth tokens in `httpOnly` cookies the browser will attach them to
any same-origin request automatically — including cross-site form posts
that an attacker can trigger. To break that vector we use the standard
double-submit pattern:

  1. On login the server sets a *non-httpOnly* `pathforge_csrf` cookie
     (random 256-bit value).
  2. JS reads that cookie and sends its value back in the
     `X-CSRF-Token` header on every state-changing request.
  3. The dependency below compares cookie-value vs header-value;
     mismatch → 403.

A cross-origin attacker cannot read the cookie (Same-origin policy
prevents JS reads of cookies on a different origin) so they cannot
forge the matching header. The cookie alone is not sufficient.

Why a separate module
---------------------
The dependency is small but is added to many routes; keeping it here
keeps the auth route file tidy and the Sentry breadcrumbs filterable
by `csrf.violation`.

Usage
-----
    from app.core.csrf import csrf_protect

    @router.post("/foo", dependencies=[Depends(csrf_protect)])
    async def foo(...): ...

Idempotent / safe methods (GET/HEAD/OPTIONS) skip CSRF entirely — the
dependency is only attached to mutating routes.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Request, status

from app.core.security import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME

logger = logging.getLogger(__name__)


async def csrf_protect(request: Request) -> None:
    """Enforce double-submit CSRF on cookie-authenticated mutating requests.

    Three branches:

    - **Header-only (legacy bearer) auth path.** If the request carries
      no `pathforge_access` cookie we *skip* CSRF — the legacy bearer
      flow is not browser-driven and CSRF doesn't apply. This keeps the
      30-day legacy header window working.
    - **Cookie auth, valid double-submit.** Cookie value is compared to
      the `X-CSRF-Token` header in constant time; match → pass.
    - **Cookie auth, mismatch.** 403 with a structured detail. Sentry
      breadcrumb tags `csrf.violation = mismatch | missing_header |
      missing_cookie`.

    Note: the cookie must exist for cookie-auth to be in play, so a
    request that has only the `Authorization: Bearer …` header is
    *correctly* not CSRF-protected — bearer tokens come from JS-attached
    headers, which CSRF cannot forge.
    """
    # CSRF only applies when the *effective* auth path is the cookie:
    #   - No `pathforge_access` cookie → bearer or unauthenticated. Skip.
    #   - Cookie present AND `Authorization` header present → caller is
    #     overriding cookie with explicit bearer; treat as bearer path.
    #     Skip. This also keeps every existing bearer-based test working
    #     unchanged during the 30-day legacy window.
    #   - Cookie present, no `Authorization` header → cookie path; enforce.
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    has_access_cookie = bool(request.cookies.get(ACCESS_COOKIE_NAME))
    has_bearer_header = bool(request.headers.get("authorization"))
    if not has_access_cookie or has_bearer_header:
        return

    if not cookie_token:
        logger.warning("csrf.violation=missing_cookie path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF cookie missing",
        )

    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not header_token:
        logger.warning("csrf.violation=missing_header path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token header missing",
        )

    # Constant-time compare guards against timing oracles.
    if not hmac.compare_digest(cookie_token, header_token):
        logger.warning("csrf.violation=mismatch path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch",
        )
