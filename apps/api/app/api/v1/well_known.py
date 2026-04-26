"""
PathForge API — Well-Known & Meta Endpoints
=============================================
RFC 9116 security.txt, robots.txt, and favicon handling.

These endpoints serve at the application root (no /api/v1 prefix).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from app.core.config import settings
from app.core.query_budget import route_query_budget

router = APIRouter(tags=["Well-Known"])

SECURITY_TXT_TEMPLATE = """Contact: mailto:{contact_email}
Expires: {expires}
Preferred-Languages: en, nl, tr
Canonical: https://api.pathforge.eu/.well-known/security.txt
Policy: https://pathforge.eu/security-policy
"""

ROBOTS_TXT = """# PathForge API — No crawling
# This is an API server, not a website.
User-agent: *
Disallow: /
"""


@router.get(
    "/.well-known/security.txt",
    summary="Security vulnerability disclosure (RFC 9116)",
    response_class=PlainTextResponse,
)
@route_query_budget(max_queries=4)
async def security_txt() -> PlainTextResponse:
    """Return security.txt per RFC 9116 for responsible disclosure."""
    expires_date = datetime.now(tz=UTC) + timedelta(days=settings.security_txt_expires_days)
    content = SECURITY_TXT_TEMPLATE.format(
        contact_email=settings.security_contact_email,
        expires=expires_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    )
    return PlainTextResponse(content=content.strip())


@router.get(
    "/robots.txt",
    summary="Robots exclusion protocol",
    response_class=PlainTextResponse,
)
@route_query_budget(max_queries=4)
async def robots_txt() -> PlainTextResponse:
    """Disallow all crawlers — this is an API, not a website."""
    return PlainTextResponse(content=ROBOTS_TXT.strip())


@router.get(
    "/favicon.ico",
    summary="Favicon (no content)",
    include_in_schema=False,
)
@route_query_budget(max_queries=4)
async def favicon() -> Response:
    """Return 204 No Content to suppress favicon 404 noise."""
    return Response(status_code=204)
