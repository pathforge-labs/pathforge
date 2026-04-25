"""
PathForge — Feature Gate Tests
================================
Sprint 35: Tests for tier-based feature gating logic.

Coverage targets:
    - feature_gate.py: ≥90%

Audit findings tested:
    CI1 — Config sync assertion (engine counts match frontend pricing.ts)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.core.feature_gate import (
    TIER_ENGINES,
    TIER_SCAN_LIMITS,
    check_engine_access,
    get_scan_limit,
    get_user_tier,
)

# ── Tier Engine Matrix Tests ────────────────────────────────


class TestTierEngines:
    """Validate tier → engine access matrix."""

    def test_free_tier_has_two_engines(self) -> None:
        """Free tier should only have career_dna and threat_radar."""
        assert len(TIER_ENGINES["free"]) == 2
        assert "career_dna" in TIER_ENGINES["free"]
        assert "threat_radar" in TIER_ENGINES["free"]

    def test_pro_tier_has_ten_engines(self) -> None:
        """Pro tier should have 10 engines."""
        assert len(TIER_ENGINES["pro"]) == 10

    def test_premium_tier_has_twelve_engines(self) -> None:
        """Premium tier should have 12 engines (all available)."""
        assert len(TIER_ENGINES["premium"]) == 12

    def test_tier_hierarchy_is_superset(self) -> None:
        """Each higher tier should be a superset of the lower tier."""
        assert TIER_ENGINES["free"].issubset(TIER_ENGINES["pro"])
        assert TIER_ENGINES["pro"].issubset(TIER_ENGINES["premium"])

    def test_premium_exclusive_engines(self) -> None:
        """career_passport and predictive_career are premium-only."""
        premium_only = TIER_ENGINES["premium"] - TIER_ENGINES["pro"]
        assert "career_passport" in premium_only
        assert "predictive_career" in premium_only


# ── Scan Limits Tests ───────────────────────────────────────


class TestScanLimits:
    """Validate tier scan limits."""

    def test_free_tier_limit(self) -> None:
        """Free tier: 3 scans per month."""
        assert TIER_SCAN_LIMITS["free"] == 3

    def test_pro_tier_limit(self) -> None:
        """Pro tier: 30 scans per month."""
        assert TIER_SCAN_LIMITS["pro"] == 30

    def test_premium_tier_unlimited(self) -> None:
        """Premium tier: unlimited scans (None)."""
        assert TIER_SCAN_LIMITS["premium"] is None

    def test_get_scan_limit_unknown_tier(self) -> None:
        """Unknown tier should default to free limit."""
        assert get_scan_limit("nonexistent") == 3


# ── get_user_tier Tests ─────────────────────────────────────


class TestGetUserTier:
    """Validate user tier resolution logic."""

    def test_billing_disabled_returns_free(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When billing is disabled, always return 'free'."""
        monkeypatch.setattr(settings, "billing_enabled", False)
        user = MagicMock()
        assert get_user_tier(user) == "free"

    def test_no_subscription_returns_free(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """User without subscription defaults to 'free'."""
        monkeypatch.setattr(settings, "billing_enabled", True)
        user = MagicMock(spec=[])  # No subscription attribute
        assert get_user_tier(user) == "free"

    def test_active_subscription_returns_tier(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Active subscription should return the subscription tier."""
        monkeypatch.setattr(settings, "billing_enabled", True)
        user = MagicMock()
        user.subscription.status = "active"
        user.subscription.tier = "pro"
        assert get_user_tier(user) == "pro"

    def test_trialing_subscription_returns_tier(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Trialing subscription should return the subscription tier."""
        monkeypatch.setattr(settings, "billing_enabled", True)
        user = MagicMock()
        user.subscription.status = "trialing"
        user.subscription.tier = "premium"
        assert get_user_tier(user) == "premium"

    def test_canceled_subscription_returns_free(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Canceled subscription should fall back to 'free'."""
        monkeypatch.setattr(settings, "billing_enabled", True)
        user = MagicMock()
        user.subscription.status = "canceled"
        user.subscription.tier = "pro"
        assert get_user_tier(user) == "free"

    def test_past_due_subscription_returns_free(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Past due subscription should fall back to 'free'."""
        monkeypatch.setattr(settings, "billing_enabled", True)
        user = MagicMock()
        user.subscription.status = "past_due"
        user.subscription.tier = "pro"
        assert get_user_tier(user) == "free"


# ── check_engine_access Tests ───────────────────────────────


class TestCheckEngineAccess:
    """Validate engine access checks."""

    def test_free_can_access_career_dna(self) -> None:
        assert check_engine_access("free", "career_dna") is True

    def test_free_cannot_access_skill_decay(self) -> None:
        assert check_engine_access("free", "skill_decay") is False

    def test_pro_can_access_salary_intelligence(self) -> None:
        assert check_engine_access("pro", "salary_intelligence") is True

    def test_pro_cannot_access_career_passport(self) -> None:
        assert check_engine_access("pro", "career_passport") is False

    def test_premium_can_access_all(self) -> None:
        """Premium tier should have access to all defined engines."""
        for engine in TIER_ENGINES["premium"]:
            assert check_engine_access("premium", engine) is True

    def test_unknown_tier_defaults_to_free(self) -> None:
        """Unknown tiers should only access free-tier engines."""
        assert check_engine_access("nonexistent", "career_dna") is True
        assert check_engine_access("nonexistent", "skill_decay") is False


# ── Config Sync Validation (CI1) ────────────────────────────


class TestConfigSync:
    """CI1: Validate backend config matches frontend pricing expectations."""

    def test_engine_count_per_tier_matches_contract(self) -> None:
        """Engine counts must match frontend pricing.ts contract.

        These assertions ensure backend and frontend stay synchronized.
        If this test fails, both TIER_ENGINES (backend) and PRICING_TIERS
        (frontend) need to be updated together.
        """
        assert len(TIER_ENGINES["free"]) == 2, "Free tier: 2 engines"
        assert len(TIER_ENGINES["pro"]) == 10, "Pro tier: 10 engines"
        assert len(TIER_ENGINES["premium"]) == 12, "Premium tier: 12 engines"

    def test_scan_limits_match_contract(self) -> None:
        """Scan limits must match frontend pricing.ts contract."""
        assert TIER_SCAN_LIMITS["free"] == 3
        assert TIER_SCAN_LIMITS["pro"] == 30
        assert TIER_SCAN_LIMITS["premium"] is None

    def test_all_tiers_defined(self) -> None:
        """All three tiers must be defined in both matrices."""
        expected_tiers = {"free", "pro", "premium"}
        assert set(TIER_ENGINES.keys()) == expected_tiers
        assert set(TIER_SCAN_LIMITS.keys()) == expected_tiers
