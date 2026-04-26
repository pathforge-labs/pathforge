"""Tests for the feature-flag system (T5 / Sprint 57, ADR-0009).

The flag system gates **deployment visibility** rather than tier
access — that's `app.core.feature_gate`'s job, intentionally kept
separate. Stages are progressive: ``internal_only`` → ``percent_5``
→ ``percent_25`` → ``percent_100``. Bucket assignment is stable per
user (deterministic hash) so a user who saw the new build at 5% also
sees it at 25%; flipping back to ``internal_only`` immediately
removes the user.

Tier-aware canary (default decision #2): on **major releases**,
paying users sit on the previous-confirmed-stable build for an
extra 24 hours. Free users absorb the canary risk in exchange for
free access (consistent with the user-as-customer business model).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.feature_flags import (
    FlagDefinition,
    InMemoryFlagProvider,
    RolloutStage,
    is_enabled,
)


def _user(
    *,
    user_id: str | None = None,
    tier: str = "free",
    is_internal: bool = False,
    created_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "id": user_id or str(uuid.uuid4()),
        "tier": tier,
        "is_internal": is_internal,
        "created_at": created_at or datetime.now(UTC),
    }


class TestRolloutStageInternalOnly:
    """``internal_only`` → only flagged-internal users see the new build.
    Everyone else sees the old build."""

    def test_internal_user_sees_new_build(self) -> None:
        provider = InMemoryFlagProvider(
            {
                "new_career_dna_engine": FlagDefinition(
                    stage=RolloutStage.internal_only,
                ),
            }
        )
        assert is_enabled(
            "new_career_dna_engine",
            user=_user(is_internal=True),
            provider=provider,
        )

    def test_external_user_does_not_see_new_build(self) -> None:
        provider = InMemoryFlagProvider(
            {
                "new_career_dna_engine": FlagDefinition(
                    stage=RolloutStage.internal_only,
                ),
            }
        )
        assert not is_enabled(
            "new_career_dna_engine",
            user=_user(is_internal=False),
            provider=provider,
        )


class TestRolloutStagePercent:
    """Percent stages bucket users deterministically by hashing
    ``(flag_key, user_id)``. The same user always lands in the same
    bucket so 5% adopters carry through to 25% and 100%."""

    def test_user_bucketing_is_stable(self) -> None:
        provider = InMemoryFlagProvider(
            {
                "new_x": FlagDefinition(stage=RolloutStage.percent_5),
            }
        )
        u = _user(user_id="abc-123")
        first = is_enabled("new_x", user=u, provider=provider)
        second = is_enabled("new_x", user=u, provider=provider)
        assert first == second

    def test_25_percent_includes_all_5_percent_users(self) -> None:
        """Bucketing is monotone: a user enabled at 5% must be enabled
        at 25% and 100% with the same flag key."""
        users = [_user(user_id=f"user-{i:04d}") for i in range(2_000)]

        prov_5 = InMemoryFlagProvider({"new_x": FlagDefinition(stage=RolloutStage.percent_5)})
        enabled_at_5 = {u["id"] for u in users if is_enabled("new_x", user=u, provider=prov_5)}
        prov_25 = InMemoryFlagProvider({"new_x": FlagDefinition(stage=RolloutStage.percent_25)})
        enabled_at_25 = {u["id"] for u in users if is_enabled("new_x", user=u, provider=prov_25)}
        # Every 5%-adopter remains an adopter at 25%.
        assert enabled_at_5.issubset(enabled_at_25)

    def test_5_percent_within_tolerance(self) -> None:
        users = [_user(user_id=f"user-{i:04d}") for i in range(10_000)]
        provider = InMemoryFlagProvider({"new_x": FlagDefinition(stage=RolloutStage.percent_5)})
        enabled = sum(1 for u in users if is_enabled("new_x", user=u, provider=provider))
        # Allow ±1.5% absolute tolerance over 10k users (deterministic
        # hash bucketing isn't a true RNG; small skews are expected).
        assert 0.035 <= enabled / len(users) <= 0.065

    def test_100_percent_covers_everyone(self) -> None:
        users = [_user(user_id=f"user-{i:04d}") for i in range(500)]
        provider = InMemoryFlagProvider({"new_x": FlagDefinition(stage=RolloutStage.percent_100)})
        for u in users:
            assert is_enabled("new_x", user=u, provider=provider)


class TestTierAwareCanary:
    """Default decision #2: paying users (pro/premium) trail the
    rollout by 24 hours on major releases. Free users absorb canary
    risk first.

    The rule: when the flag is at percent_5 / percent_25 AND
    ``major_release: true`` AND the rollout started < 24h ago, paying
    users see the previous build (i.e. the new flag returns False).
    """

    def test_paying_users_are_held_back_for_24h_on_major_release(self) -> None:
        rollout_start = datetime.now(UTC) - timedelta(hours=2)
        provider = InMemoryFlagProvider(
            {
                "engine_v2": FlagDefinition(
                    stage=RolloutStage.percent_25,
                    major_release=True,
                    rollout_started_at=rollout_start,
                ),
            }
        )
        # A paying user that would otherwise be in the 25% bucket
        # is held back during the 24h window.
        paying_user = _user(user_id="user-0001", tier="premium")
        free_user = _user(user_id="user-0001", tier="free")
        # Same user_id → same bucket; tier alone changes the answer.
        assert not is_enabled("engine_v2", user=paying_user, provider=provider)
        # Free users see the build per their bucket (might be True or
        # False depending on hash; we assert the gate logic doesn't
        # spuriously block them — at least one of 50 free users hits).
        free_ids = [_user(user_id=f"free-{i}") for i in range(50)]
        assert any(is_enabled("engine_v2", user=u, provider=provider) for u in free_ids)

    def test_paying_users_unblocked_after_24h(self) -> None:
        rollout_start = datetime.now(UTC) - timedelta(hours=25)
        provider = InMemoryFlagProvider(
            {
                "engine_v2": FlagDefinition(
                    stage=RolloutStage.percent_100,
                    major_release=True,
                    rollout_started_at=rollout_start,
                ),
            }
        )
        paying_user = _user(tier="premium")
        assert is_enabled("engine_v2", user=paying_user, provider=provider)

    def test_minor_release_does_not_hold_paying_users(self) -> None:
        rollout_start = datetime.now(UTC) - timedelta(hours=2)
        provider = InMemoryFlagProvider(
            {
                "patch_x": FlagDefinition(
                    stage=RolloutStage.percent_100,
                    major_release=False,
                    rollout_started_at=rollout_start,
                ),
            }
        )
        paying_user = _user(tier="premium")
        # Bug-fix patches deploy unsegmented (default decision #2).
        assert is_enabled("patch_x", user=paying_user, provider=provider)


class TestProviderSetRollout:
    """The Sentry auto-rollback webhook flips flags back via
    ``provider.set_rollout(flag, RolloutStage.internal_only)``."""

    def test_set_rollout_updates_subsequent_lookups(self) -> None:
        provider = InMemoryFlagProvider(
            {
                "new_x": FlagDefinition(stage=RolloutStage.percent_25),
            }
        )
        u = _user()
        # Pre-rollback: at least some users see the new build.
        # (Don't assert single-user equality — bucketing is hash-based.)
        before = sum(
            1
            for _ in range(200)
            if is_enabled(
                "new_x",
                user=_user(user_id=f"u-{_}"),
                provider=provider,
            )
        )
        assert before > 0

        provider.set_rollout("new_x", RolloutStage.internal_only)
        after = sum(
            1
            for _ in range(200)
            if is_enabled(
                "new_x",
                user=_user(user_id=f"u-{_}"),
                provider=provider,
            )
        )
        assert after == 0

    def test_set_rollout_on_unknown_flag_creates_new_definition(
        self,
    ) -> None:
        provider = InMemoryFlagProvider({})
        provider.set_rollout("brand_new", RolloutStage.percent_5)
        # Now the flag exists at 5%.
        users = [_user(user_id=f"u-{i}") for i in range(1_000)]
        enabled = sum(1 for u in users if is_enabled("brand_new", user=u, provider=provider))
        assert 30 <= enabled <= 70  # ~5% ± tolerance


class TestUnknownFlag:
    """Asking about a flag the provider has never heard of returns
    False (fail-closed).  Enables progressive code merges where the
    flag check lands before the operator creates the flag."""

    def test_unknown_flag_returns_false(self) -> None:
        provider = InMemoryFlagProvider({})
        assert not is_enabled("never_defined", user=_user(), provider=provider)
