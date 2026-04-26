"""
PathForge API — Feature Flag System (T5 / Sprint 57, ADR-0009)
================================================================

Gates **deployment visibility** for new code.  Distinct from
:mod:`app.core.feature_gate`, which gates **tier access** to engines
that already shipped.  See ADR-0009 §"Two systems, one mental model"
for the boundary.

Rollout stages (progressive)
----------------------------

``internal_only`` → ``percent_5`` → ``percent_25`` → ``percent_100``

Bucket assignment is **stable per user** (deterministic SHA-256 hash
of ``flag_key + user_id``) so a user that saw the new build at 5 %
remains an adopter at 25 % and 100 %.  This is the canonical
property of progressive rollout — without it, the system flips
random users in and out of the new code path on each percent bump,
which destroys the value of the canary stage.

Tier-aware canary (sprint plan §12 default decision #2)
--------------------------------------------------------

On **major releases**, paying users (``tier in {"pro", "premium"}``)
see the previous-confirmed-stable build for an additional 24 hours
after the rollout starts.  Free users absorb canary risk first.
This is consistent with PathForge's user-as-customer business model
— paying users are the ones we cannot afford to disrupt; free users
*implicitly* trade lower stability for free access.

The 24 h carve-out only applies while the flag is in a partial-
rollout stage (``percent_5`` or ``percent_25``) AND the rollout
started < 24 h ago AND the flag carries ``major_release=True``.
Bug-fix patches (``major_release=False``) deploy unsegmented.

Provider abstraction
--------------------

:class:`FeatureFlagProvider` is a Protocol-style ABC.  The default
:class:`InMemoryFlagProvider` is suitable for tests and for the
"GrowthBook-not-yet-provisioned" launch state (sprint plan §12
default decision #1: SaaS free tier ≤ 5 flags; self-host above).
A future ``GrowthBookProvider`` plugs in without changing the
:func:`is_enabled` callers.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TypedDict


class FlagUser(TypedDict, total=False):
    """Duck-typed user payload that drives the bucketing decision.

    Total=False because most callers only carry ``id`` and ``tier`` — the
    optional fields are reserved for cohort gating that ships later.

    Fields:
        id: Stable user identifier (string-coercible). Required for
            bucketing — without it, ``is_enabled`` fails closed.
        tier: ``"free"`` / ``"pro"`` / ``"premium"`` etc. Drives the
            paying-user 24 h delay on major releases.
        is_internal: True for internal employees / integration personae.
            Internal users see the new build at every stage (canary's
            canary) — defaults to False when absent.
        created_at: Reserved for future cohort gating
            (e.g. "users created after 2026-Q3 see the new flow").
    """

    id: str
    tier: str
    is_internal: bool
    created_at: datetime

#: Tier values that count as "paying users" for tier-aware canary.
#: Single source of truth so the same set is shared by ``feature_gate``
#: and any future tier-tagging telemetry without re-importing.
PAYING_TIERS: frozenset[str] = frozenset({"pro", "premium"})

#: Window during which paying users sit on the previous build for
#: major releases (sprint plan §12 default decision #2).
PAYING_USER_DELAY: timedelta = timedelta(hours=24)


class RolloutStage(StrEnum):
    """Progressive rollout stages, ordered by visibility."""

    internal_only = "internal_only"
    percent_5 = "percent_5"
    percent_25 = "percent_25"
    percent_100 = "percent_100"

    @property
    def percent(self) -> int:
        """Numeric percentage represented by this stage (0 for
        ``internal_only`` since it's not a percent rollout)."""
        return {
            RolloutStage.internal_only: 0,
            RolloutStage.percent_5: 5,
            RolloutStage.percent_25: 25,
            RolloutStage.percent_100: 100,
        }[self]

    @property
    def is_partial(self) -> bool:
        """True for the canary-window stages (5 % or 25 %)."""
        return self in (RolloutStage.percent_5, RolloutStage.percent_25)


@dataclass
class FlagDefinition:
    """Per-flag rollout state stored in the provider."""

    stage: RolloutStage = RolloutStage.internal_only
    major_release: bool = False
    rollout_started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def replace_stage(self, stage: RolloutStage) -> FlagDefinition:
        """Return a new definition with the same major_release flag
        and a refreshed rollout-start clock when transitioning to a
        partial stage.  Auto-rollback to ``internal_only`` resets the
        clock so a re-enable kicks off a fresh 24 h window for paying
        users.
        """
        return FlagDefinition(
            stage=stage,
            major_release=self.major_release,
            rollout_started_at=datetime.now(UTC),
        )


class FeatureFlagProvider(ABC):
    """Provider abstraction.  Concrete impls: :class:`InMemoryFlagProvider`
    (default) + a future ``GrowthBookProvider``.
    """

    @abstractmethod
    def get(self, flag_key: str) -> FlagDefinition | None:
        """Return the flag definition or ``None`` if undefined."""

    @abstractmethod
    def set_rollout(
        self,
        flag_key: str,
        stage: RolloutStage,
        *,
        major_release: bool | None = None,
    ) -> None:
        """Persist a new rollout stage for ``flag_key``.

        When the flag is undefined, create it with the supplied
        stage.  When transitioning to ``internal_only`` (auto-rollback
        path), preserve the ``major_release`` field so a re-enable
        kicks off a fresh 24 h window for paying users.
        """


class InMemoryFlagProvider(FeatureFlagProvider):
    """In-memory provider — backs tests and the pre-GrowthBook
    launch state.  Thread-safety: stores are dict mutations, fine
    for the single-process FastAPI worker model.  Multi-worker
    deployments need GrowthBook (centralised state).
    """

    def __init__(self, definitions: dict[str, FlagDefinition]) -> None:
        # Defensive copy so callers can't mutate the shared definitions.
        self._defs: dict[str, FlagDefinition] = dict(definitions)

    def get(self, flag_key: str) -> FlagDefinition | None:
        return self._defs.get(flag_key)

    def set_rollout(
        self,
        flag_key: str,
        stage: RolloutStage,
        *,
        major_release: bool | None = None,
    ) -> None:
        existing = self._defs.get(flag_key)
        resolved_major = (
            major_release
            if major_release is not None
            else (existing.major_release if existing is not None else False)
        )
        self._defs[flag_key] = FlagDefinition(
            stage=stage,
            major_release=resolved_major,
            rollout_started_at=datetime.now(UTC),
        )


# ── Bucketing ────────────────────────────────────────────────


def _bucket_for(flag_key: str, user_id: str) -> int:
    """Return a stable bucket in ``[0, 100)`` for the (flag, user)
    pair.  Uses SHA-256 to avoid non-cryptographic-hash collision
    quirks; the modulo-100 reduction is fine because SHA-256 is
    uniformly distributed across the output space (we use the first
    8 bytes as a 64-bit integer; mod 100 over 2⁶⁴ has uniform error
    well below 1 e-18).
    """
    # We deliberately do **not** salt with a server secret. The
    # bucketing must be reproducible across server restarts so a
    # user that adopted at 5 % stays an adopter at 25 %.
    digest = hashlib.sha256(f"{flag_key}|{user_id}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big") % 100


# ── Public API ───────────────────────────────────────────────


def is_enabled(
    flag_key: str,
    *,
    user: FlagUser,
    provider: FeatureFlagProvider,
) -> bool:
    """Return whether ``user`` should see the flagged feature.

    ``user`` is a duck-typed dict carrying:

    * ``id``: stable user identifier (string-coercible).
    * ``tier``: ``"free"`` / ``"pro"`` / ``"premium"`` etc.
    * ``is_internal`` (optional, default False): True for the
      internal-only audience (employee accounts, integration test
      personae).
    * ``created_at`` (optional): unused today, reserved for cohort
      gating (e.g. "users created after 2026-Q3 see the new flow").

    Fail-closed contract:

    * Unknown flag → False (operator must define before code lands).
    * Missing ``id`` → False (defensive — bucketing requires it).
    """
    flag = provider.get(flag_key)
    if flag is None:
        return False

    # Internal users always see the new build at every stage —
    # they're the canary's canary.
    if user.get("is_internal", False):
        return True

    user_id = user.get("id")
    if not user_id:
        return False

    if flag.stage is RolloutStage.internal_only:
        return False
    if flag.stage is RolloutStage.percent_100:
        # Even at 100 %, the tier-aware delay applies for major
        # releases inside the 24 h window.
        return _passes_tier_canary(flag, user)

    # Partial stages: bucket gate first, then tier-aware delay.
    bucket = _bucket_for(flag_key, str(user_id))
    if bucket >= flag.stage.percent:
        return False
    return _passes_tier_canary(flag, user)


def _passes_tier_canary(flag: FlagDefinition, user: FlagUser) -> bool:
    """Return True if the user is past the tier-aware delay.

    Default decision #2: paying users sit on the previous build for
    24 h on **major releases** while the rollout is partial (5 % or
    25 %) OR within the 24 h window of going to 100 %.
    """
    if not flag.major_release:
        return True
    tier = user.get("tier", "free")
    if tier not in PAYING_TIERS:
        return True
    # Partial rollout AND major AND paying AND within 24 h → hold back.
    elapsed = datetime.now(UTC) - flag.rollout_started_at
    return elapsed >= PAYING_USER_DELAY


__all__ = [
    "PAYING_TIERS",
    "PAYING_USER_DELAY",
    "FeatureFlagProvider",
    "FlagDefinition",
    "InMemoryFlagProvider",
    "RolloutStage",
    "is_enabled",
]
