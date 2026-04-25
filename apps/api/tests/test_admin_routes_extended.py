"""
PathForge — Admin API Route Extended Tests
==============================================
Extended coverage for ``app.api.v1.admin`` route branches not covered by
``test_admin.py``.

Covers:
    * ``require_admin`` dependency (admin-pass, non-admin 403)
    * 401 (unauthenticated) for every admin endpoint
    * 403 (non-admin role) for every admin endpoint
    * Happy paths for each endpoint with ``AdminService`` mocked
    * Error translations (ValueError → 404 / 400)

Mocks ``AdminService`` staticmethods to avoid exercising service-layer logic
already covered by ``test_admin_service.py``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    *,
    email: str,
    role: str = UserRole.USER.value,
    is_active: bool = True,
    is_verified: bool = True,
) -> User:
    """Insert a user row directly for route-level tests."""
    user = User(
        email=email,
        full_name="Route Test User",
        hashed_password=hash_password("TestPass123!"),
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    """Return a bearer-token header for the given user."""
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Admin user persisted for route-level RBAC tests."""
    return await _make_user(
        db_session,
        email="route-admin@pathforge.eu",
        role=UserRole.ADMIN.value,
    )


@pytest.fixture
async def admin_headers(admin_user: User) -> dict[str, str]:
    """Bearer token headers for the admin user."""
    return _auth_headers(admin_user)


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Non-admin user persisted for negative RBAC tests."""
    return await _make_user(
        db_session,
        email="route-user@pathforge.eu",
        role=UserRole.USER.value,
    )


@pytest.fixture
async def regular_headers(regular_user: User) -> dict[str, str]:
    """Bearer token headers for a regular (non-admin) user."""
    return _auth_headers(regular_user)


def _stub_detail(user_id: str | None = None) -> dict[str, Any]:
    """Build a dict that satisfies ``AdminUserDetailResponse``."""
    return {
        "id": uuid.UUID(user_id) if user_id else uuid.uuid4(),
        "email": "stub@pathforge.eu",
        "full_name": "Stub Detail",
        "role": UserRole.USER.value,
        "is_active": True,
        "is_verified": True,
        "auth_provider": "email",
        "created_at": datetime.now(UTC),
        "subscription_tier": "free",
        "subscription_status": "active",
        "scans_used": 3,
    }


def _stub_summary() -> dict[str, Any]:
    """Minimal ``AdminUserSummary`` compatible dict."""
    return {
        "id": uuid.uuid4(),
        "email": "summary@pathforge.eu",
        "full_name": "Stub Summary",
        "role": UserRole.USER.value,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.now(UTC),
    }


# ── require_admin Dependency ──────────────────────────────────


class TestRequireAdminDependency:
    """Direct exercise of the ``require_admin`` dependency function."""

    async def test_require_admin_passes_for_admin_user(
        self, admin_user: User,
    ) -> None:
        """Admin role should pass through unchanged."""
        from app.api.v1.admin import require_admin

        result = await require_admin(current_user=admin_user)
        assert result is admin_user
        assert result.role == UserRole.ADMIN.value

    async def test_require_admin_rejects_regular_user(
        self, regular_user: User,
    ) -> None:
        """Non-admin should raise 403."""
        from fastapi import HTTPException

        from app.api.v1.admin import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=regular_user)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail


# ── 401: Unauthenticated Access ───────────────────────────────


class TestAdminEndpointsRequireAuth:
    """Every admin endpoint must reject unauthenticated callers."""

    async def test_dashboard_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401

    async def test_list_users_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 401

    async def test_user_detail_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get(
            f"/api/v1/admin/users/{uuid.uuid4()}",
        )
        assert response.status_code == 401

    async def test_update_user_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.patch(
            f"/api/v1/admin/users/{uuid.uuid4()}",
            json={"is_active": False},
        )
        assert response.status_code == 401

    async def test_override_subscription_unauthenticated(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            f"/api/v1/admin/users/{uuid.uuid4()}/subscription",
            json={"tier": "pro", "reason": "test"},
        )
        assert response.status_code == 401

    async def test_system_health_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/health")
        assert response.status_code == 401

    async def test_audit_logs_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 401


# ── 403: Non-Admin Role Forbidden ─────────────────────────────


class TestAdminEndpointsRequireAdminRole:
    """Authenticated users without admin role must receive 403."""

    async def test_dashboard_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.get(
            "/api/v1/admin/dashboard", headers=regular_headers,
        )
        assert response.status_code == 403

    async def test_list_users_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.get(
            "/api/v1/admin/users", headers=regular_headers,
        )
        assert response.status_code == 403

    async def test_user_detail_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.get(
            f"/api/v1/admin/users/{uuid.uuid4()}",
            headers=regular_headers,
        )
        assert response.status_code == 403

    async def test_update_user_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.patch(
            f"/api/v1/admin/users/{uuid.uuid4()}",
            headers=regular_headers,
            json={"is_active": False},
        )
        assert response.status_code == 403

    async def test_override_subscription_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.post(
            f"/api/v1/admin/users/{uuid.uuid4()}/subscription",
            headers=regular_headers,
            json={"tier": "pro", "reason": "bump"},
        )
        assert response.status_code == 403

    async def test_system_health_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.get(
            "/api/v1/admin/health", headers=regular_headers,
        )
        assert response.status_code == 403

    async def test_audit_logs_regular_user_forbidden(
        self, client: AsyncClient, regular_headers: dict[str, str],
    ) -> None:
        response = await client.get(
            "/api/v1/admin/audit-logs", headers=regular_headers,
        )
        assert response.status_code == 403


# ── Happy Paths (Admin + Mocked Service) ──────────────────────


class TestAdminDashboard:
    """Dashboard summary endpoint happy/unhappy paths."""

    async def test_dashboard_returns_200_with_summary(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        payload = {
            "total_users": 42,
            "active_users": 30,
            "tier_distribution": {"free": 30, "pro": 10, "premium": 2},
            "total_scans_this_period": 100,
            "waitlist_count": 7,
        }
        with patch(
            "app.api.v1.admin.AdminService.get_dashboard_summary",
            new=AsyncMock(return_value=payload),
        ):
            response = await client.get(
                "/api/v1/admin/dashboard", headers=admin_headers,
            )
        assert response.status_code == 200
        body = response.json()
        assert body["total_users"] == 42
        assert body["tier_distribution"]["pro"] == 10


class TestAdminListUsers:
    """User listing endpoint happy paths including filters."""

    async def test_list_users_default_pagination(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        mock_response = {
            "users": [_stub_summary()],
            "total": 1,
            "page": 1,
            "per_page": 20,
        }
        with patch(
            "app.api.v1.admin.AdminService.list_users",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            response = await client.get(
                "/api/v1/admin/users", headers=admin_headers,
            )
        assert response.status_code == 200
        args = mocked.call_args.args
        # db, page, per_page, search, role
        assert args[1] == 1
        assert args[2] == 20
        assert args[3] is None
        assert args[4] is None

    async def test_list_users_passes_filters(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        mock_response = {
            "users": [],
            "total": 0,
            "page": 2,
            "per_page": 5,
        }
        with patch(
            "app.api.v1.admin.AdminService.list_users",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            response = await client.get(
                "/api/v1/admin/users",
                headers=admin_headers,
                params={
                    "page": 2,
                    "per_page": 5,
                    "search": "alice",
                    "role": "admin",
                },
            )
        assert response.status_code == 200
        args = mocked.call_args.args
        assert args[1] == 2
        assert args[2] == 5
        assert args[3] == "alice"
        assert args[4] == "admin"


class TestAdminUserDetail:
    """User-detail endpoint happy/unhappy paths."""

    async def test_user_detail_returns_200(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        target_id = str(uuid.uuid4())
        stub = _stub_detail(user_id=target_id)
        with patch(
            "app.api.v1.admin.AdminService.get_user_detail",
            new=AsyncMock(return_value=stub),
        ):
            response = await client.get(
                f"/api/v1/admin/users/{target_id}",
                headers=admin_headers,
            )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == target_id
        assert body["email"] == "stub@pathforge.eu"

    async def test_user_detail_missing_returns_404(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        """ValueError from service → 404."""
        with patch(
            "app.api.v1.admin.AdminService.get_user_detail",
            new=AsyncMock(side_effect=ValueError("user not found")),
        ):
            response = await client.get(
                f"/api/v1/admin/users/{uuid.uuid4()}",
                headers=admin_headers,
            )
        assert response.status_code == 404
        assert "user not found" in response.json()["detail"]


class TestAdminUpdateUser:
    """PATCH /admin/users/{id} happy and error branches."""

    async def test_update_user_happy_path_returns_detail(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        target_id = str(uuid.uuid4())
        fake_user = type("U", (), {"id": uuid.UUID(target_id)})()
        stub = _stub_detail(user_id=target_id)
        with (
            patch(
                "app.api.v1.admin.AdminService.update_user",
                new=AsyncMock(return_value=fake_user),
            ) as update_mock,
            patch(
                "app.api.v1.admin.AdminService.get_user_detail",
                new=AsyncMock(return_value=stub),
            ) as detail_mock,
        ):
            response = await client.patch(
                f"/api/v1/admin/users/{target_id}",
                headers=admin_headers,
                json={"is_active": False, "role": "admin"},
            )
        assert response.status_code == 200
        assert response.json()["id"] == target_id
        # ``exclude_none`` means is_verified must not be in the dict.
        assert update_mock.called
        updates = update_mock.call_args.args[3]
        assert updates == {"is_active": False, "role": "admin"}
        assert detail_mock.called

    async def test_update_user_value_error_returns_400(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        with patch(
            "app.api.v1.admin.AdminService.update_user",
            new=AsyncMock(side_effect=ValueError("cannot self-demote")),
        ):
            response = await client.patch(
                f"/api/v1/admin/users/{uuid.uuid4()}",
                headers=admin_headers,
                json={"role": "user"},
            )
        assert response.status_code == 400
        assert "cannot self-demote" in response.json()["detail"]

    async def test_update_user_rejects_invalid_role(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        """Schema regex should reject unknown role without hitting service."""
        with patch(
            "app.api.v1.admin.AdminService.update_user",
            new=AsyncMock(),
        ) as mocked:
            response = await client.patch(
                f"/api/v1/admin/users/{uuid.uuid4()}",
                headers=admin_headers,
                json={"role": "superuser"},
            )
        assert response.status_code == 422
        assert not mocked.called


class TestAdminOverrideSubscription:
    """Subscription-override endpoint happy and validation paths."""

    async def test_override_subscription_returns_ok(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        target_id = str(uuid.uuid4())
        with patch(
            "app.api.v1.admin.AdminService.override_subscription",
            new=AsyncMock(return_value=None),
        ) as mocked:
            response = await client.post(
                f"/api/v1/admin/users/{target_id}/subscription",
                headers=admin_headers,
                json={"tier": "premium", "reason": "VIP customer"},
            )
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "tier": "premium"}
        # admin, user_id, tier, reason (positional args 1..4)
        args = mocked.call_args.args
        assert args[2] == target_id
        assert args[3] == "premium"
        assert args[4] == "VIP customer"

    async def test_override_subscription_invalid_tier_422(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        with patch(
            "app.api.v1.admin.AdminService.override_subscription",
            new=AsyncMock(),
        ) as mocked:
            response = await client.post(
                f"/api/v1/admin/users/{uuid.uuid4()}/subscription",
                headers=admin_headers,
                json={"tier": "enterprise", "reason": "x"},
            )
        assert response.status_code == 422
        assert not mocked.called

    async def test_override_subscription_missing_reason_422(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        with patch(
            "app.api.v1.admin.AdminService.override_subscription",
            new=AsyncMock(),
        ) as mocked:
            response = await client.post(
                f"/api/v1/admin/users/{uuid.uuid4()}/subscription",
                headers=admin_headers,
                json={"tier": "pro"},
            )
        assert response.status_code == 422
        assert not mocked.called


class TestAdminSystemHealth:
    """System-health endpoint happy path."""

    async def test_system_health_returns_200(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        stub = {
            "database": "ok",
            "redis": "ok",
            "stripe": "configured",
            "worker": "unknown",
        }
        with patch(
            "app.api.v1.admin.AdminService.get_system_health",
            new=AsyncMock(return_value=stub),
        ):
            response = await client.get(
                "/api/v1/admin/health", headers=admin_headers,
            )
        assert response.status_code == 200
        body = response.json()
        assert body["database"] == "ok"
        assert body["stripe"] == "configured"


class TestAdminAuditLogs:
    """Audit-log listing endpoint happy path and pagination."""

    async def test_audit_logs_default_pagination(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        with patch(
            "app.api.v1.admin.AdminService.list_audit_logs",
            new=AsyncMock(return_value=[]),
        ) as mocked:
            response = await client.get(
                "/api/v1/admin/audit-logs", headers=admin_headers,
            )
        assert response.status_code == 200
        assert response.json() == []
        args = mocked.call_args.args
        assert args[1] == 1
        assert args[2] == 20

    async def test_audit_logs_forwards_pagination(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        entry = {
            "id": uuid.uuid4(),
            "admin_user_id": uuid.uuid4(),
            "action": "user.update",
            "target_user_id": uuid.uuid4(),
            "details": {"field": "is_active"},
            "ip_address": "127.0.0.1",
            "created_at": datetime.now(UTC),
        }
        with patch(
            "app.api.v1.admin.AdminService.list_audit_logs",
            new=AsyncMock(return_value=[entry]),
        ) as mocked:
            response = await client.get(
                "/api/v1/admin/audit-logs",
                headers=admin_headers,
                params={"page": 3, "per_page": 50},
            )
        assert response.status_code == 200
        assert len(response.json()) == 1
        args = mocked.call_args.args
        assert args[1] == 3
        assert args[2] == 50

    async def test_audit_logs_with_null_optional_fields(
        self, client: AsyncClient, admin_headers: dict[str, str],
    ) -> None:
        """Entries with null target_user_id / details / ip still serialize."""
        entry = {
            "id": uuid.uuid4(),
            "admin_user_id": uuid.uuid4(),
            "action": "system.boot",
            "target_user_id": None,
            "details": None,
            "ip_address": None,
            "created_at": datetime.now(UTC),
        }
        with patch(
            "app.api.v1.admin.AdminService.list_audit_logs",
            new=AsyncMock(return_value=[entry]),
        ):
            response = await client.get(
                "/api/v1/admin/audit-logs", headers=admin_headers,
            )
        assert response.status_code == 200
        body = response.json()
        assert body[0]["action"] == "system.boot"
        assert body[0]["target_user_id"] is None
        assert body[0]["details"] is None
