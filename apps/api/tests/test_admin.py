"""
PathForge — Admin API Tests
================================
Sprint 35: Tests for admin endpoints across billing, users, and system.

Coverage: admin.py (Sprint 34)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ── Admin Access Control Tests ──────────────────────────────


@pytest.mark.asyncio
class TestAdminAccess:
    """Admin endpoints should be restricted to admin users."""

    async def test_dashboard_non_admin_returns_403(
        self, auth_client: AsyncClient,
    ) -> None:
        """Non-admin user should be rejected from admin dashboard."""
        response = await auth_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403

    async def test_users_list_non_admin_returns_403(
        self, auth_client: AsyncClient,
    ) -> None:
        """Non-admin user should be rejected from user listing."""
        response = await auth_client.get("/api/v1/admin/users")
        assert response.status_code == 403

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient,
    ) -> None:
        """Unauthenticated requests should return 401."""
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401

    async def test_admin_user_detail_non_admin(
        self, auth_client: AsyncClient,
    ) -> None:
        """Non-admin requesting user detail should be rejected."""
        response = await auth_client.get(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_admin_subscription_override_non_admin(
        self, auth_client: AsyncClient,
    ) -> None:
        """Non-admin cannot override subscriptions."""
        response = await auth_client.post(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000000001/subscription",
            json={"tier": "pro"},
        )
        assert response.status_code == 403

    async def test_admin_billing_events_non_admin(
        self, auth_client: AsyncClient,
    ) -> None:
        """Non-admin cannot access billing events."""
        response = await auth_client.get("/api/v1/admin/billing-events")
        # Admin billing-events endpoint, should be 403 or 404
        assert response.status_code in (403, 404)
