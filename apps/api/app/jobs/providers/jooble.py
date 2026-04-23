"""
PathForge — Jooble Job Provider
==================================
Integration with Jooble API for job listing aggregation.

API Docs: https://jooble.org/api/about
Auth: API key in URL path
Rate Limits: undocumented — conservative 10/min default
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings
from app.core.redis_ssl import resolve_redis_url
from app.jobs.providers.base import RawJobListing

logger = logging.getLogger(__name__)

BASE_URL = "https://jooble.org/api"


class JoobleProvider:
    """
    Jooble API job search provider.

    Uses POST requests with JSON body for search queries.

    Usage:
        provider = JoobleProvider()
        jobs = await provider.search(keywords="python developer", location="Amsterdam")
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.jooble_api_key
        self._client: httpx.AsyncClient | None = None
        self._breaker = CircuitBreaker(
            name="jooble",
            redis_url=resolve_redis_url(
                settings.redis_url,
                settings.redis_ssl_enabled,
                settings.environment,
            ),
        )

    @property
    def name(self) -> str:
        return "jooble"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def search(
        self,
        *,
        keywords: str,
        location: str = "",
        country: str = "nl",
        page: int = 1,
        results_per_page: int = 20,
    ) -> list[RawJobListing]:
        """
        Search Jooble for jobs.

        POST https://jooble.org/api/{api_key}
        """
        url = f"{BASE_URL}/{self._api_key}"

        body: dict[str, Any] = {
            "keywords": keywords,
            "page": str(page),
            "searchMode": 1,  # 1 = Regular search
        }
        if location:
            body["location"] = location

        client = self._get_client()
        try:
            async with self._breaker:
                response = await client.post(url, json=body)
                if 400 <= response.status_code < 500:
                    logger.error("Jooble API client error %d", response.status_code)
                    return []
                response.raise_for_status()  # 5xx propagates → trips breaker
                data = response.json()
        except CircuitOpenError as exc:
            logger.warning("Jooble circuit open, skipping search: %s", exc)
            return []
        except httpx.HTTPStatusError as exc:
            logger.error("Jooble API server error %d: %s", exc.response.status_code, str(exc)[:200])
            return []
        except httpx.RequestError as exc:
            logger.error("Jooble request failed: %s", str(exc)[:200])
            return []

        jobs = data.get("jobs", [])
        logger.info("Jooble returned %d results for '%s'", len(jobs), keywords)
        return [self._map_result(r) for r in jobs]

    @staticmethod
    def _map_result(raw: dict[str, Any]) -> RawJobListing:
        """Map Jooble API response to normalized RawJobListing."""
        return RawJobListing(
            title=raw.get("title", "").strip(),
            company=raw.get("company", "").strip(),
            description=raw.get("snippet", "").strip(),
            location=raw.get("location", "").strip(),
            work_type=raw.get("type", ""),
            salary_info=raw.get("salary", ""),
            source_url=raw.get("link", ""),
            source_platform="jooble",
            external_id=str(raw.get("id", "")),
            extra={
                "updated": raw.get("updated", ""),
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
