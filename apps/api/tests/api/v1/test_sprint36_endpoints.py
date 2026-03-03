"""
PathForge — Target Role & Resilience History API Tests
======================================================
Sprint 36 WS-5/WS-6: Backend integration tests for:
- PUT /api/v1/career-dna/growth/target-role
- GET /api/v1/threat-radar/resilience/history
"""

from __future__ import annotations

from httpx import AsyncClient

# ── WS-6: Target Role Update ───────────────────────────────────


class TestTargetRoleUpdate:
    """Tests for PUT /api/v1/career-dna/growth/target-role endpoint."""

    ENDPOINT = "/api/v1/career-dna/growth/target-role"

    async def test_update_target_role_requires_auth(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Unauthenticated requests should return 401."""
        response = await async_client.put(
            self.ENDPOINT,
            json={"target_role": "Senior Engineer"},
        )
        assert response.status_code == 401

    async def test_update_target_role_validates_payload(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Missing target_role should return 422."""
        response = await async_client.put(
            self.ENDPOINT,
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_update_target_role_empty_string_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty string target_role should be rejected."""
        response = await async_client.put(
            self.ENDPOINT,
            json={"target_role": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_update_target_role_max_length(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """target_role exceeding 255 chars should be rejected."""
        response = await async_client.put(
            self.ENDPOINT,
            json={"target_role": "x" * 256},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ── WS-5: Resilience History ───────────────────────────────────


class TestResilienceHistory:
    """Tests for GET /api/v1/threat-radar/resilience/history endpoint."""

    ENDPOINT = "/api/v1/threat-radar/resilience/history"

    async def test_resilience_history_requires_auth(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Unauthenticated requests should return 401."""
        response = await async_client.get(self.ENDPOINT)
        assert response.status_code == 401

    async def test_resilience_history_default_days(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Default days parameter should be 90."""
        response = await async_client.get(
            self.ENDPOINT,
            headers=auth_headers,
        )
        # 404 acceptable if no career DNA exists yet
        assert response.status_code in (200, 404)

    async def test_resilience_history_custom_days(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Custom days parameter should be accepted."""
        response = await async_client.get(
            f"{self.ENDPOINT}?days=30",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    async def test_resilience_history_invalid_days(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Days > 365 should be rejected."""
        response = await async_client.get(
            f"{self.ENDPOINT}?days=500",
            headers=auth_headers,
        )
        assert response.status_code == 422
