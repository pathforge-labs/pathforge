"""
PathForge — Adzuna Job Provider
==================================
Integration with Adzuna API v1 for job listing aggregation.

API Docs: https://developer.adzuna.com/
Auth: app_id + app_key as query parameters
Rate Limits: 25/min, 250/day (default tier)
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

# Adzuna country code mapping (API uses different codes)
ADZUNA_COUNTRIES = {
    "nl": "nl",
    "gb": "gb",
    "us": "us",
    "de": "de",
    "fr": "fr",
    "au": "au",
    "ca": "ca",
    "in": "in",
}

BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaProvider:
    """
    Adzuna API v1 job search provider.

    Handles authentication, response parsing, and mapping to RawJobListing.

    Usage:
        provider = AdzunaProvider()
        jobs = await provider.search(keywords="python developer", country="nl")
    """

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
    ) -> None:
        self._app_id = app_id or settings.adzuna_app_id
        self._app_key = app_key or settings.adzuna_app_key
        self._client: httpx.AsyncClient | None = None
        self._breaker = CircuitBreaker(
            name="adzuna",
            redis_url=resolve_redis_url(
                settings.redis_url,
                settings.redis_ssl_enabled,
                settings.environment,
            ),
        )

    @property
    def name(self) -> str:
        return "adzuna"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"Accept": "application/json"},
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
        Search Adzuna for jobs.

        GET /v1/api/jobs/{country}/search/{page}
        """
        adzuna_country = ADZUNA_COUNTRIES.get(country, country)
        url = f"{BASE_URL}/{adzuna_country}/search/{page}"

        params: dict[str, Any] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": min(results_per_page, 50),  # API max is 50
            "what": keywords,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        client = self._get_client()
        try:
            async with self._breaker:
                response = await client.get(url, params=params)
                if 400 <= response.status_code < 500:
                    logger.error("Adzuna API client error %d", response.status_code)
                    return []
                response.raise_for_status()  # 5xx propagates → trips breaker
                data = response.json()
        except CircuitOpenError as exc:
            logger.warning("Adzuna circuit open, skipping search: %s", exc)
            return []
        except httpx.HTTPStatusError as exc:
            logger.error("Adzuna API server error %d: %s", exc.response.status_code, str(exc)[:200])
            return []
        except httpx.RequestError as exc:
            logger.error("Adzuna request failed: %s", str(exc)[:200])
            return []

        results = data.get("results", [])
        logger.info("Adzuna returned %d results for '%s' in %s", len(results), keywords, country)
        return [self._map_result(r) for r in results]

    @staticmethod
    def _map_result(raw: dict[str, Any]) -> RawJobListing:
        """Map Adzuna API response to normalized RawJobListing."""
        location_parts = []
        loc_data = raw.get("location", {})
        if loc_data.get("display_name"):
            location_parts.append(loc_data["display_name"])

        return RawJobListing(
            title=raw.get("title", "").strip(),
            company=raw.get("company", {}).get("display_name", "").strip(),
            description=raw.get("description", "").strip(),
            location=", ".join(location_parts) if location_parts else "",
            work_type=raw.get("contract_type", "") or raw.get("contract_time", ""),
            salary_info=_format_salary(raw),
            source_url=raw.get("redirect_url", ""),
            source_platform="adzuna",
            external_id=str(raw.get("id", "")),
            extra={
                "category": raw.get("category", {}).get("label", ""),
                "created": raw.get("created", ""),
                "latitude": raw.get("latitude"),
                "longitude": raw.get("longitude"),
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


def _format_salary(raw: dict[str, Any]) -> str:
    """Format salary range from Adzuna response."""
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    if salary_min and salary_max:
        return f"€{salary_min:,.0f} - €{salary_max:,.0f}"
    if salary_min:
        return f"€{salary_min:,.0f}+"
    return ""
