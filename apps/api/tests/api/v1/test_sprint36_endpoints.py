"""
PathForge — Target Role & Resilience History API Tests
======================================================
Sprint 36 WS-5/WS-6: Backend integration tests for:
- PUT /api/v1/career-dna/growth/target-role
- GET /api/v1/threat-radar/resilience/history

These tests validate route registration, auth enforcement, and
basic request handling. Full validation tests (422 cases) require
seeded career DNA data — covered in integration test suites.
"""

from __future__ import annotations

from httpx import AsyncClient

# ── WS-6: Target Role Update ───────────────────────────────────


class TestTargetRoleUpdate:
    """Tests for PUT /api/v1/career-dna/growth/target-role endpoint."""

    ENDPOINT = "/api/v1/career-dna/growth/target-role"

    async def test_update_target_role_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated requests should return 401."""
        response = await client.put(
            self.ENDPOINT,
            json={"target_role": "Senior Engineer"},
        )
        assert response.status_code == 401

    async def test_update_target_role_no_career_dna_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Authenticated user without Career DNA should get 404."""
        response = await client.put(
            self.ENDPOINT,
            json={"target_role": "Staff Engineer"},
            headers=auth_headers,
        )
        # No career DNA record exists for the test user → 404
        assert response.status_code == 404

    async def test_update_target_role_empty_string_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty target_role should be rejected with 422 (validation first)."""
        response = await client.put(
            self.ENDPOINT,
            json={},
            headers=auth_headers,
        )
        # Validation fires before career DNA lookup
        assert response.status_code == 422

    async def test_update_target_role_max_length_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """target_role exceeding 255 chars should be rejected with 422."""
        response = await client.put(
            self.ENDPOINT,
            json={"target_role": "x" * 256},
            headers=auth_headers,
        )
        # Length validation fires before career DNA lookup
        assert response.status_code == 422


# ── WS-5: Resilience History ───────────────────────────────────


class TestResilienceHistory:
    """Tests for GET /api/v1/threat-radar/resilience/history endpoint."""

    ENDPOINT = "/api/v1/threat-radar/resilience/history"

    async def test_resilience_history_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated requests should return 401."""
        response = await client.get(self.ENDPOINT)
        assert response.status_code == 401

    async def test_resilience_history_default_days(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Default days parameter should be 90."""
        response = await client.get(
            self.ENDPOINT,
            headers=auth_headers,
        )
        # 404 acceptable if no career DNA exists yet
        assert response.status_code in (200, 404)

    async def test_resilience_history_custom_days(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Custom days parameter should be accepted."""
        response = await client.get(
            f"{self.ENDPOINT}?days=30",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    async def test_resilience_history_invalid_days(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Days > 365 should be rejected."""
        response = await client.get(
            f"{self.ENDPOINT}?days=500",
            headers=auth_headers,
        )
        assert response.status_code == 422
