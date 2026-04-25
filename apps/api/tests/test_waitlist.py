"""
PathForge — Waitlist API Tests
================================
Sprint 35: Tests for waitlist endpoints.

Route: POST /api/v1/waitlist/join (public, rate-limited)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWaitlist:
    """POST /waitlist/join — public waitlist signup."""

    async def test_signup_success(self, client: AsyncClient) -> None:
        """Valid signup should return 201."""
        response = await client.post(
            "/api/v1/waitlist/join",
            json={"email": "waitlist@pathforge.eu", "name": "Test"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "position" in data
        assert data["email"] == "waitlist@pathforge.eu"

    async def test_signup_duplicate_prevention(self, client: AsyncClient) -> None:
        """Duplicate email should be handled gracefully (not crash)."""
        payload = {"email": "dupe@pathforge.eu", "name": "Dupe"}
        first = await client.post("/api/v1/waitlist/join", json=payload)
        assert first.status_code == 201

        second = await client.post("/api/v1/waitlist/join", json=payload)
        # Should return 409 or handle gracefully
        assert second.status_code in (200, 201, 409)

    async def test_signup_invalid_email(self, client: AsyncClient) -> None:
        """Invalid email should return validation error."""
        response = await client.post(
            "/api/v1/waitlist/join",
            json={"email": "not-an-email", "name": "Test"},
        )
        assert response.status_code == 422
