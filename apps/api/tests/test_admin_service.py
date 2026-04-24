"""
PathForge — AdminService Unit Tests
=====================================
Comprehensive tests for ``app.services.admin_service.AdminService``.

Covers:
    * list_users (search, role filter, pagination)
    * get_user_detail (with / without subscription, missing user)
    * update_user (role updates, self-demotion guard, last-admin guard,
      audit log creation, refresh behaviour)
    * override_subscription (create and update paths, audit log)
    * get_dashboard_summary (aggregate counts, tier distribution)
    * get_system_health (DB, Redis, Stripe config paths)
    * list_audit_logs (ordering, pagination)
    * auto_promote_initial_admin (empty email, missing user,
      already-admin, successful promotion)
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.admin import AdminAuditLog
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User, UserRole
from app.services.admin_service import AdminService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ───────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str = "Test User",
    role: str = UserRole.USER.value,
    is_active: bool = True,
    is_verified: bool = False,
    auth_provider: str = "email",
) -> User:
    """Insert a user row directly for service-level tests."""
    user = User(
        email=email,
        full_name=full_name,
        hashed_password="x" * 20,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        auth_provider=auth_provider,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_subscription(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tier: str = "free",
    status: str = "active",
) -> Subscription:
    sub = Subscription(user_id=user_id, tier=tier, status=status)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


# ── list_users ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListUsers:
    async def test_empty_database_returns_zero(
        self, db_session: AsyncSession,
    ) -> None:
        result = await AdminService.list_users(db_session)
        assert result["total"] == 0
        assert result["users"] == []
        assert result["page"] == 1
        assert result["per_page"] == 20

    async def test_returns_all_users_when_no_filter(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(db_session, email="a@test.io")
        await _make_user(db_session, email="b@test.io")
        result = await AdminService.list_users(db_session)
        assert result["total"] == 2
        assert len(result["users"]) == 2

    async def test_search_matches_email(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(db_session, email="alice@pathforge.eu")
        await _make_user(db_session, email="bob@pathforge.eu")
        result = await AdminService.list_users(db_session, search="alice")
        assert result["total"] == 1
        assert result["users"][0].email == "alice@pathforge.eu"

    async def test_search_matches_full_name(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(db_session, email="x@t.io", full_name="Zelda Wizard")
        await _make_user(db_session, email="y@t.io", full_name="Bob Normal")
        result = await AdminService.list_users(db_session, search="Wizard")
        assert result["total"] == 1
        assert result["users"][0].full_name == "Zelda Wizard"

    async def test_role_filter(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(db_session, email="admin@t.io", role=UserRole.ADMIN.value)
        await _make_user(db_session, email="user1@t.io")
        await _make_user(db_session, email="user2@t.io")
        result = await AdminService.list_users(
            db_session, role_filter=UserRole.ADMIN.value,
        )
        assert result["total"] == 1
        assert result["users"][0].role == UserRole.ADMIN.value

    async def test_pagination_respects_per_page(
        self, db_session: AsyncSession,
    ) -> None:
        for i in range(5):
            await _make_user(db_session, email=f"u{i}@t.io")
        result = await AdminService.list_users(db_session, per_page=2)
        assert result["total"] == 5
        assert len(result["users"]) == 2

    async def test_pagination_second_page(
        self, db_session: AsyncSession,
    ) -> None:
        for i in range(5):
            await _make_user(db_session, email=f"u{i}@t.io")
        page1 = await AdminService.list_users(db_session, page=1, per_page=2)
        page2 = await AdminService.list_users(db_session, page=2, per_page=2)
        page3 = await AdminService.list_users(db_session, page=3, per_page=2)
        assert len(page1["users"]) == 2
        assert len(page2["users"]) == 2
        assert len(page3["users"]) == 1

    async def test_search_and_role_filter_combined(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(
            db_session, email="admin-alice@t.io", role=UserRole.ADMIN.value,
        )
        await _make_user(
            db_session, email="user-alice@t.io", role=UserRole.USER.value,
        )
        await _make_user(
            db_session, email="admin-bob@t.io", role=UserRole.ADMIN.value,
        )
        result = await AdminService.list_users(
            db_session, search="alice", role_filter=UserRole.ADMIN.value,
        )
        assert result["total"] == 1
        assert result["users"][0].email == "admin-alice@t.io"


# ── get_user_detail ────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetUserDetail:
    async def test_returns_user_without_subscription(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="no-sub@t.io")
        detail = await AdminService.get_user_detail(db_session, str(user.id))
        assert detail["email"] == "no-sub@t.io"
        assert detail["subscription_tier"] is None
        assert detail["subscription_status"] is None
        assert detail["scans_used"] == 0

    async def test_returns_user_with_subscription(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pro@t.io")
        await _make_subscription(
            db_session, user_id=user.id, tier="pro", status="active",
        )
        detail = await AdminService.get_user_detail(db_session, str(user.id))
        assert detail["subscription_tier"] == "pro"
        assert detail["subscription_status"] == "active"

    async def test_missing_user_raises_value_error(
        self, db_session: AsyncSession,
    ) -> None:
        random_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="User not found"):
            await AdminService.get_user_detail(db_session, random_id)

    async def test_invalid_uuid_raises(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError):
            await AdminService.get_user_detail(db_session, "not-a-uuid")


# ── update_user ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_updates_basic_field(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        result = await AdminService.update_user(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            updates={"full_name": "New Name"},
            ip_address="1.2.3.4",
        )
        assert result.full_name == "New Name"

    async def test_creates_audit_log(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        await AdminService.update_user(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            updates={"full_name": "Audited"},
            ip_address="10.0.0.1",
        )
        from sqlalchemy import select

        logs = (
            await db_session.execute(select(AdminAuditLog))
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].action == "user_update"
        assert logs[0].ip_address == "10.0.0.1"
        assert logs[0].admin_user_id == admin.id

    async def test_missing_target_raises(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        with pytest.raises(ValueError, match="User not found"):
            await AdminService.update_user(
                db_session,
                admin_user=admin,
                target_user_id=str(uuid.uuid4()),
                updates={"full_name": "X"},
            )

    async def test_self_demotion_is_blocked(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        with pytest.raises(ValueError, match="Cannot demote yourself"):
            await AdminService.update_user(
                db_session,
                admin_user=admin,
                target_user_id=str(admin.id),
                updates={"role": UserRole.USER.value},
            )

    async def test_last_admin_demotion_blocked(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        # Even though admin is demoting *another* admin, we only have one
        # admin total, so after demotion there would be zero — blocked.
        other_admin = await _make_user(
            db_session, email="other@t.io", role=UserRole.ADMIN.value,
        )
        # Delete the first admin so only other_admin remains.
        await db_session.delete(admin)
        await db_session.flush()
        # Re-create the acting admin so admin_user is still a valid reference,
        # but now total admins = 2 so test requires setting things up right.
        acting_admin = await _make_user(
            db_session, email="acting@t.io", role=UserRole.ADMIN.value,
        )
        # Delete acting so only other_admin is admin
        # Simpler: just test directly with only one admin in DB
        await db_session.delete(acting_admin)
        await db_session.flush()

        # Now "admin_user" param is disposable — we just need the target to
        # be the sole admin. Use a fresh admin user but don't persist.
        fake_admin = User(
            email="fake-admin@t.io",
            full_name="Fake",
            hashed_password="x" * 20,
            role=UserRole.ADMIN.value,
        )
        # Don't persist fake_admin; it's only used for admin_user.id reference.
        # But admin_user.id must be set — use uuid
        fake_admin.id = uuid.uuid4()

        with pytest.raises(ValueError, match="Cannot remove the last admin"):
            await AdminService.update_user(
                db_session,
                admin_user=fake_admin,
                target_user_id=str(other_admin.id),
                updates={"role": UserRole.USER.value},
            )

    async def test_demote_admin_when_multiple_admins(
        self, db_session: AsyncSession,
    ) -> None:
        admin1 = await _make_user(
            db_session, email="a1@t.io", role=UserRole.ADMIN.value,
        )
        admin2 = await _make_user(
            db_session, email="a2@t.io", role=UserRole.ADMIN.value,
        )
        result = await AdminService.update_user(
            db_session,
            admin_user=admin1,
            target_user_id=str(admin2.id),
            updates={"role": UserRole.USER.value},
        )
        assert result.role == UserRole.USER.value

    async def test_promote_user_to_admin(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        result = await AdminService.update_user(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            updates={"role": UserRole.ADMIN.value},
        )
        assert result.role == UserRole.ADMIN.value

    async def test_none_values_ignored(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(
            db_session, email="target@t.io", full_name="Keep Me",
        )
        result = await AdminService.update_user(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            updates={"full_name": None},
        )
        assert result.full_name == "Keep Me"

    async def test_unknown_field_ignored(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        result = await AdminService.update_user(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            updates={"nonexistent_field": "xyz", "full_name": "Y"},
        )
        assert result.full_name == "Y"
        assert not hasattr(result, "nonexistent_field_value")


# ── override_subscription ──────────────────────────────────────


@pytest.mark.asyncio
class TestOverrideSubscription:
    async def test_creates_new_subscription(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        sub = await AdminService.override_subscription(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            tier="pro",
            reason="VIP upgrade",
        )
        assert sub.tier == "pro"
        assert sub.user_id == target.id
        assert sub.status == "active"

    async def test_updates_existing_subscription(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        await _make_subscription(db_session, user_id=target.id, tier="free")
        sub = await AdminService.override_subscription(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            tier="premium",
            reason="Customer complaint",
        )
        assert sub.tier == "premium"

    async def test_logs_override_action(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        target = await _make_user(db_session, email="target@t.io")
        await AdminService.override_subscription(
            db_session,
            admin_user=admin,
            target_user_id=str(target.id),
            tier="pro",
            reason="Compensation",
            ip_address="8.8.8.8",
        )
        from sqlalchemy import select

        logs = (
            await db_session.execute(select(AdminAuditLog))
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].action == "subscription_override"
        assert logs[0].ip_address == "8.8.8.8"


# ── get_dashboard_summary ──────────────────────────────────────


@pytest.mark.asyncio
class TestDashboardSummary:
    async def test_empty_database(
        self, db_session: AsyncSession,
    ) -> None:
        summary = await AdminService.get_dashboard_summary(db_session)
        assert summary["total_users"] == 0
        assert summary["active_users"] == 0
        assert summary["tier_distribution"] == {}
        assert summary["total_scans_this_period"] == 0
        assert summary["waitlist_count"] == 0

    async def test_counts_total_and_active_users(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(db_session, email="a@t.io", is_active=True)
        await _make_user(db_session, email="b@t.io", is_active=True)
        await _make_user(db_session, email="c@t.io", is_active=False)
        summary = await AdminService.get_dashboard_summary(db_session)
        assert summary["total_users"] == 3
        assert summary["active_users"] == 2

    async def test_tier_distribution(
        self, db_session: AsyncSession,
    ) -> None:
        u1 = await _make_user(db_session, email="a@t.io")
        u2 = await _make_user(db_session, email="b@t.io")
        u3 = await _make_user(db_session, email="c@t.io")
        await _make_subscription(db_session, user_id=u1.id, tier="free")
        await _make_subscription(db_session, user_id=u2.id, tier="pro")
        await _make_subscription(db_session, user_id=u3.id, tier="pro")
        summary = await AdminService.get_dashboard_summary(db_session)
        assert summary["tier_distribution"]["free"] == 1
        assert summary["tier_distribution"]["pro"] == 2

    async def test_total_scans_sum(
        self, db_session: AsyncSession,
    ) -> None:
        from datetime import UTC, datetime, timedelta

        user = await _make_user(db_session, email="u@t.io")
        sub = await _make_subscription(db_session, user_id=user.id)
        now = datetime.now(UTC)
        later = now + timedelta(days=30)
        db_session.add(
            UsageRecord(
                user_id=user.id,
                subscription_id=sub.id,
                period_start=now,
                period_end=now + timedelta(days=29),
                scan_count=7,
            ),
        )
        db_session.add(
            UsageRecord(
                user_id=user.id,
                subscription_id=sub.id,
                period_start=later,
                period_end=later + timedelta(days=29),
                scan_count=3,
            ),
        )
        await db_session.flush()
        summary = await AdminService.get_dashboard_summary(db_session)
        assert summary["total_scans_this_period"] == 10


# ── get_system_health ──────────────────────────────────────────


@pytest.mark.asyncio
class TestSystemHealth:
    async def test_healthy_db_when_query_succeeds(
        self, db_session: AsyncSession,
    ) -> None:
        # Redis is unavailable in tests; it will be "unhealthy".
        health = await AdminService.get_system_health(db_session)
        assert health["database"] == "healthy"
        assert health["redis"] in {"healthy", "unhealthy"}
        assert health["stripe"] in {"configured", "not_configured"}
        assert "worker" in health

    async def test_unhealthy_db_on_exception(self) -> None:
        bad_session = MagicMock()
        bad_session.execute = AsyncMock(side_effect=RuntimeError("boom"))
        health = await AdminService.get_system_health(bad_session)
        assert health["database"] == "unhealthy"

    async def test_redis_healthy_when_ping_succeeds(
        self, db_session: AsyncSession,
    ) -> None:
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        with patch(
            "app.core.token_blacklist.token_blacklist.get_redis",
            new=AsyncMock(return_value=mock_redis),
        ):
            health = await AdminService.get_system_health(db_session)
        assert health["redis"] == "healthy"

    async def test_redis_unhealthy_when_ping_raises(
        self, db_session: AsyncSession,
    ) -> None:
        with patch(
            "app.core.token_blacklist.token_blacklist.get_redis",
            new=AsyncMock(side_effect=RuntimeError("no redis")),
        ):
            health = await AdminService.get_system_health(db_session)
        assert health["redis"] == "unhealthy"

    async def test_stripe_configured(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_xyz")
        health = await AdminService.get_system_health(db_session)
        assert health["stripe"] == "configured"

    async def test_stripe_not_configured(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "stripe_secret_key", "")
        health = await AdminService.get_system_health(db_session)
        assert health["stripe"] == "not_configured"


# ── list_audit_logs ────────────────────────────────────────────


@pytest.mark.asyncio
class TestListAuditLogs:
    async def test_empty_returns_empty_list(
        self, db_session: AsyncSession,
    ) -> None:
        logs = await AdminService.list_audit_logs(db_session)
        assert logs == []

    async def test_returns_log_entries(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        for i in range(3):
            db_session.add(
                AdminAuditLog(
                    admin_user_id=admin.id,
                    action=f"action_{i}",
                    target_user_id=None,
                    details={"n": str(i)},
                ),
            )
        await db_session.flush()
        logs = await AdminService.list_audit_logs(db_session)
        assert len(logs) == 3

    async def test_pagination(
        self, db_session: AsyncSession,
    ) -> None:
        admin = await _make_user(
            db_session, email="admin@t.io", role=UserRole.ADMIN.value,
        )
        for i in range(5):
            db_session.add(
                AdminAuditLog(
                    admin_user_id=admin.id,
                    action=f"action_{i}",
                    target_user_id=None,
                ),
            )
        await db_session.flush()
        page1 = await AdminService.list_audit_logs(
            db_session, page=1, per_page=2,
        )
        page2 = await AdminService.list_audit_logs(
            db_session, page=2, per_page=2,
        )
        page3 = await AdminService.list_audit_logs(
            db_session, page=3, per_page=2,
        )
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1


# ── auto_promote_initial_admin ─────────────────────────────────


@pytest.mark.asyncio
class TestAutoPromoteInitialAdmin:
    async def test_empty_email_returns_false(
        self, db_session: AsyncSession,
    ) -> None:
        assert await AdminService.auto_promote_initial_admin(
            db_session, "",
        ) is False

    async def test_none_like_falsy_returns_false(
        self, db_session: AsyncSession,
    ) -> None:
        # Type is str per signature, but empty is the documented "skip" path.
        result = await AdminService.auto_promote_initial_admin(db_session, "")
        assert result is False

    async def test_unknown_email_returns_false(
        self, db_session: AsyncSession,
    ) -> None:
        assert await AdminService.auto_promote_initial_admin(
            db_session, "nobody@pathforge.eu",
        ) is False

    async def test_already_admin_returns_false(
        self, db_session: AsyncSession,
    ) -> None:
        await _make_user(
            db_session, email="boss@t.io", role=UserRole.ADMIN.value,
        )
        assert await AdminService.auto_promote_initial_admin(
            db_session, "boss@t.io",
        ) is False

    async def test_promotes_user_to_admin(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="future-admin@t.io")
        assert user.role == UserRole.USER.value
        result = await AdminService.auto_promote_initial_admin(
            db_session, "future-admin@t.io",
        )
        assert result is True
        await db_session.refresh(user)
        assert user.role == UserRole.ADMIN.value
