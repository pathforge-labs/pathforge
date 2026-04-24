"""
PathForge API — Users & Waitlist Endpoint Extended Tests
=========================================================
Extended coverage for gaps in ``test_users.py`` and ``test_waitlist.py``:

* ``DELETE /api/v1/users/me``  — GDPR Article 17 account deletion
* ``PATCH  /api/v1/users/me``  — profile update parity
* ``GET    /api/v1/waitlist/position`` — public waitlist lookup
* ``GET    /api/v1/waitlist/stats``    — admin authentication guard
* ``GET    /api/v1/waitlist/entries``  — admin authentication guard
* ``POST   /api/v1/waitlist/invite``   — admin authentication guard

Admin-authenticated happy paths are intentionally skipped here because
``conftest.py`` does not expose an ``admin_headers`` fixture; adding
one belongs to a dedicated admin-testing sprint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Constants ─────────────────────────────────────────────────────

USERS_ME = "/api/v1/users/me"
WAITLIST_JOIN = "/api/v1/waitlist/join"
WAITLIST_POSITION = "/api/v1/waitlist/position"
WAITLIST_STATS = "/api/v1/waitlist/stats"
WAITLIST_ENTRIES = "/api/v1/waitlist/entries"
WAITLIST_INVITE = "/api/v1/waitlist/invite"

MOCK_DELETE_RESULT = {
    "records_deleted": 42,
    "tables_affected": ["users", "resumes"],
}

DELETION_SERVICE_PATH = (
    "app.services.account_deletion_service.AccountDeletionService.delete_account"
)
TOKEN_BLACKLIST_PATH = "app.core.token_blacklist.TokenBlacklist.revoke"


# ══════════════════════════════════════════════════════════════════
# DELETE /api/v1/users/me  — GDPR Article 17
# ══════════════════════════════════════════════════════════════════


class TestDeleteAccount:
    """DELETE /users/me — account deletion endpoint."""

    async def test_delete_account_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        """Unauthenticated DELETE returns 401."""
        response = await client.delete(USERS_ME)
        assert response.status_code == 401

    async def test_delete_account_success(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Authenticated DELETE returns 200 with deleted=True."""
        with (
            patch(
                DELETION_SERVICE_PATH,
                new_callable=AsyncMock,
                return_value=MOCK_DELETE_RESULT,
            ),
            patch(TOKEN_BLACKLIST_PATH, new_callable=AsyncMock),
        ):
            response = await client.delete(USERS_ME, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["deleted"] is True
        assert "records_deleted" in body
        assert "tables_affected" in body

    async def test_delete_account_response_structure(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Response contains the full GDPR confirmation payload."""
        with (
            patch(
                DELETION_SERVICE_PATH,
                new_callable=AsyncMock,
                return_value=MOCK_DELETE_RESULT,
            ),
            patch(TOKEN_BLACKLIST_PATH, new_callable=AsyncMock),
        ):
            response = await client.delete(USERS_ME, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        required_keys = {"deleted", "message", "records_deleted", "tables_affected"}
        assert required_keys.issubset(body.keys())
        assert body["records_deleted"] == 42
        assert body["tables_affected"] == ["users", "resumes"]
        assert isinstance(body["message"], str)
        assert body["message"]  # non-empty

    async def test_delete_account_blacklists_token(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """token_blacklist.revoke is awaited with the current token's jti."""
        revoke_mock = AsyncMock()
        with (
            patch(
                DELETION_SERVICE_PATH,
                new_callable=AsyncMock,
                return_value=MOCK_DELETE_RESULT,
            ),
            patch(TOKEN_BLACKLIST_PATH, revoke_mock),
        ):
            response = await client.delete(USERS_ME, headers=auth_headers)

        assert response.status_code == 200
        assert revoke_mock.await_count == 1
        # revoke is called as revoke(jti, ttl_seconds=3600)
        _args, kwargs = revoke_mock.await_args
        assert kwargs.get("ttl_seconds") == 3600

    async def test_delete_account_handles_blacklist_failure_gracefully(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """If token_blacklist.revoke raises, the endpoint still returns 200."""
        with (
            patch(
                DELETION_SERVICE_PATH,
                new_callable=AsyncMock,
                return_value=MOCK_DELETE_RESULT,
            ),
            patch(
                TOKEN_BLACKLIST_PATH,
                new_callable=AsyncMock,
                side_effect=RuntimeError("redis unavailable"),
            ),
        ):
            response = await client.delete(USERS_ME, headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["deleted"] is True


# ══════════════════════════════════════════════════════════════════
# PATCH /api/v1/users/me  — parity coverage
# ══════════════════════════════════════════════════════════════════


class TestUpdateMeExtended:
    """Additional PATCH /users/me cases not covered by test_users.py."""

    async def test_update_me_returns_updated_payload(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """PATCH with full_name returns the updated user object (200)."""
        response = await client.patch(
            USERS_ME,
            headers=auth_headers,
            json={"full_name": "Extended Suite"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Extended Suite"
        assert "email" in data
        assert "id" in data


# ══════════════════════════════════════════════════════════════════
# GET /api/v1/waitlist/position  — public lookup
# ══════════════════════════════════════════════════════════════════


class TestWaitlistPosition:
    """GET /waitlist/position — public email → position lookup."""

    async def test_check_position_found(self, client: AsyncClient) -> None:
        """A previously joined email yields its waitlist entry."""
        email = "position-found@pathforge.eu"
        join_response = await client.post(
            WAITLIST_JOIN,
            json={"email": email, "full_name": "Found User"},
        )
        assert join_response.status_code == 201

        response = await client.get(
            WAITLIST_POSITION, params={"email": email},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert isinstance(data["position"], int)
        assert data["position"] >= 1
        assert "status" in data

    async def test_check_position_not_found(self, client: AsyncClient) -> None:
        """Unknown email yields 404."""
        response = await client.get(
            WAITLIST_POSITION,
            params={"email": "ghost@pathforge.eu"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_check_position_no_email_param(
        self, client: AsyncClient,
    ) -> None:
        """Missing required ``email`` query param yields 422."""
        response = await client.get(WAITLIST_POSITION)
        assert response.status_code == 422

    async def test_check_position_case_insensitive(
        self, client: AsyncClient,
    ) -> None:
        """Waitlist lookup normalises email case (F27)."""
        email = "MixedCase@pathforge.eu"
        join_response = await client.post(
            WAITLIST_JOIN, json={"email": email},
        )
        assert join_response.status_code == 201

        response = await client.get(
            WAITLIST_POSITION,
            params={"email": "mixedcase@PATHFORGE.EU"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == email.lower()


# ══════════════════════════════════════════════════════════════════
# Admin waitlist endpoints  — authentication guards
# ══════════════════════════════════════════════════════════════════


class TestWaitlistAdminAuth:
    """Ensure admin waitlist endpoints reject unauthenticated callers."""

    async def test_get_waitlist_stats_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get(WAITLIST_STATS)
        assert response.status_code == 401

    async def test_list_waitlist_entries_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get(WAITLIST_ENTRIES)
        assert response.status_code == 401

    async def test_invite_batch_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(WAITLIST_INVITE, json={"count": 5})
        assert response.status_code == 401

    async def test_list_waitlist_entries_rejects_invalid_token(
        self, client: AsyncClient,
    ) -> None:
        """Malformed bearer token is rejected upstream (401)."""
        headers = {"Authorization": "Bearer not-a-real-jwt"}
        response = await client.get(WAITLIST_ENTRIES, headers=headers)
        assert response.status_code == 401

    async def test_get_waitlist_stats_forbidden_for_non_admin(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Non-admin authenticated user cannot view waitlist stats (403)."""
        response = await client.get(WAITLIST_STATS, headers=auth_headers)
        assert response.status_code == 403

    async def test_list_waitlist_entries_forbidden_for_non_admin(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Non-admin authenticated user cannot list waitlist entries (403)."""
        response = await client.get(WAITLIST_ENTRIES, headers=auth_headers)
        assert response.status_code == 403

    async def test_invite_batch_forbidden_for_non_admin(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Non-admin authenticated user cannot invite batches (403)."""
        response = await client.post(
            WAITLIST_INVITE,
            headers=auth_headers,
            json={"count": 5},
        )
        assert response.status_code == 403

    async def test_invite_batch_validates_count_lower_bound(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Count < 1 is rejected by pydantic before reaching the admin guard (422)."""
        response = await client.post(
            WAITLIST_INVITE,
            headers=auth_headers,
            json={"count": 0},
        )
        assert response.status_code == 422

    async def test_invite_batch_validates_count_upper_bound(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Count > 100 is rejected by pydantic (422)."""
        response = await client.post(
            WAITLIST_INVITE,
            headers=auth_headers,
            json={"count": 101},
        )
        assert response.status_code == 422
