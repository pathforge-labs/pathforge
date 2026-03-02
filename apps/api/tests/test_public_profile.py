"""
PathForge — Public Profile API Tests
=======================================
Sprint 35: Tests for public profile endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPublicProfile:
    """GET /users/profile/:slug — public profile access."""

    async def test_nonexistent_slug_returns_404(self, client: AsyncClient) -> None:
        """Requesting a non-existent slug should return 404."""
        response = await client.get("/api/v1/users/profile/nonexistent-slug")
        assert response.status_code == 404

    async def test_public_profile_unauthenticated(
        self, client: AsyncClient,
    ) -> None:
        """Public profiles should be accessible without authentication."""
        response = await client.get("/api/v1/users/profile/test-user")
        # Should return 404 (not 401) — proving auth is not required
        assert response.status_code == 404
