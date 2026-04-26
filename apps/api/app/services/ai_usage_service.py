"""
PathForge — AI Usage Service (T4 / Sprint 56, ADR-0008)
=========================================================

Aggregates :class:`app.models.ai_transparency.AITransparencyRecord`
rows into per-engine, per-period usage summaries.  Powers the
**Transparent AI Accounting** dashboard at
``GET /api/v1/ai-usage/summary``.

Tier presentation
-----------------

The response carries **both** scan counts (free tier signal) and
estimated EUR cost (premium tier signal) per the decision default
in ``docs/architecture/sprint-55-58-code-side-readiness.md`` §12 (#4
= dual-display).  The web layer chooses which to surface based on
the caller's subscription tier; the API does not gate.

Cost computation
----------------

Cost is derived from ``prompt_tokens`` × prompt-rate +
``completion_tokens`` × completion-rate, indexed by the recorded
``model`` name.  Unknown models contribute to the call count but
not to the cost total — the summary carries
:attr:`UsageSummary.has_unpriced_models` so the UI can warn "cost
estimate unavailable" rather than silently under-report.

Why server-side computation (vs. recording cost at call time)
-------------------------------------------------------------

* Prices change retroactively (Anthropic / Google / Voyage all
  re-tier periodically). Re-pricing historical records on price-table
  refresh requires the source of truth to be tokens-and-model, not a
  pre-computed cost column.
* Cost is a **derived** quantity. Storing it would create a
  consistency hazard between the column and the price table.

The trade-off is one extra multiplication per record at read time —
negligible for the per-user, per-month aggregate workload.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_transparency import AITransparencyRecord

#: USD → EUR conversion. Pinned constant rather than live FX so the
#: same record always reports the same EUR figure (audit invariant).
#: Refresh quarterly with the rest of the cost table.
EUR_PER_USD: float = 0.94

# ── Model price table ──────────────────────────────────────────
#
# Prices in **USD per 1M tokens** as of 2026-04-25.  Refresh
# quarterly — see ``docs/baselines/README.md`` for the cadence
# rationale (same trigger conditions: provider price change OR every
# 4 sprints minimum).
#
# Format: ``MODEL_PRICES_USD_PER_1M[model_name] = (input, output)``
# Lookup is **prefix-match-friendliest-wins** so model alias drift
# doesn't immediately disable cost reporting (e.g. a
# ``claude-sonnet-4-6-20260101`` alias still hits the
# ``claude-sonnet-4`` row).

_PRICE_TABLE: dict[str, tuple[Decimal, Decimal]] = {
    # Anthropic
    "claude-haiku-4-5": (Decimal("1.00"), Decimal("5.00")),
    "claude-sonnet-4-6": (Decimal("3.00"), Decimal("15.00")),
    "claude-sonnet-4-5": (Decimal("3.00"), Decimal("15.00")),
    "claude-sonnet-4": (Decimal("3.00"), Decimal("15.00")),
    "claude-opus-4-7": (Decimal("15.00"), Decimal("75.00")),
    "claude-opus-4-6": (Decimal("15.00"), Decimal("75.00")),
    # Google
    "gemini-2-5-flash": (Decimal("0.075"), Decimal("0.30")),
    "gemini-2-5-pro": (Decimal("1.25"), Decimal("5.00")),
    # Voyage AI (embeddings — output rate is 0)
    "voyage-3": (Decimal("0.06"), Decimal("0.00")),
    "voyage-large-2": (Decimal("0.12"), Decimal("0.00")),
}


def _resolve_price(model: str) -> tuple[Decimal, Decimal] | None:
    """Resolve a model name to (input_per_1m_usd, output_per_1m_usd).

    Tries an exact match first, then progressively shorter prefixes so
    model-version aliases (``claude-sonnet-4-5-20260415``) still map
    to a base entry.  Returns ``None`` for unknown models.
    """
    if not model:
        return None
    if model in _PRICE_TABLE:
        return _PRICE_TABLE[model]
    parts = model.split("-")
    while len(parts) > 1:
        parts.pop()
        candidate = "-".join(parts)
        if candidate in _PRICE_TABLE:
            return _PRICE_TABLE[candidate]
    return None


# ── Period helper ──────────────────────────────────────────────


@dataclass(frozen=True)
class UsagePeriod:
    """A half-open ``[start, end)`` window over which the summary is
    computed.  Stored as UTC datetimes so the SQL filter is timezone-
    aware on every backend.
    """

    start: datetime
    end: datetime
    label: str

    @classmethod
    def current_month(cls, now: datetime | None = None) -> UsagePeriod:
        ref = now or datetime.now(UTC)
        start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # End = first day of next month, midnight UTC.
        last_day = calendar.monthrange(ref.year, ref.month)[1]
        end = start.replace(day=last_day) + (
            datetime.max.replace(year=ref.year) - datetime.max.replace(year=ref.year)
        )
        # Cleaner: start of the month + relativedelta-style 1-month bump
        if ref.month == 12:
            end = start.replace(year=ref.year + 1, month=1)
        else:
            end = start.replace(month=ref.month + 1)
        return cls(start=start, end=end, label="current_month")


# ── Response types ──────────────────────────────────────────────


@dataclass
class EngineUsage:
    """Per-engine usage row in the summary response."""

    engine: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_eur_cents: int
    avg_latency_ms: int
    last_call_at: datetime | None


@dataclass
class UsageSummary:
    """Aggregated AI usage for a single user × period."""

    user_id: str
    period_label: str
    period_start: datetime
    period_end: datetime
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_eur_cents: int
    has_unpriced_models: bool
    engines: list[EngineUsage] = field(default_factory=list)


# ── Internal aggregation bucket ─────────────────────────────────


@dataclass
class _EngineBucket:
    """Mutable per-engine accumulator used during aggregation. Kept
    private — the public response shape is :class:`EngineUsage`.
    """

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd_cents: Decimal = field(default_factory=lambda: Decimal("0"))
    latency_total_ms: int = 0
    last_call_at: datetime | None = None


# ── Service ────────────────────────────────────────────────────


class AIUsageService:
    """Per-user aggregator over :class:`AITransparencyRecord`."""

    #: Column subset selected for cost computation. Module-level so
    #: tests can patch in alternate price tables without re-creating
    #: the SQL projection.
    _SELECTED_COLUMNS: ClassVar[tuple[str, ...]] = (
        "analysis_type",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "created_at",
    )

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def summary(
        self,
        *,
        user_id: object,
        period: UsagePeriod,
    ) -> UsageSummary:
        """Aggregate a user's AI usage over ``period``.

        ``user_id`` is typed ``object`` because callers pass either
        :class:`uuid.UUID` (from the route handler's ``current_user``)
        or string (from JSON-flowing call sites). SQLAlchemy's UUID
        column accepts both.
        """
        stmt = (
            select(AITransparencyRecord)
            .where(AITransparencyRecord.user_id == user_id)
            .where(AITransparencyRecord.created_at >= period.start)
            .where(AITransparencyRecord.created_at < period.end)
            .order_by(AITransparencyRecord.created_at)
        )
        result = await self._db.execute(stmt)
        records = list(result.scalars().all())

        # Group by engine (`analysis_type`) — tabulate counts, tokens,
        # latencies, last_call_at, and accumulate cost in **USD cents**
        # (Decimal) to avoid float drift, then convert to EUR cents at
        # the end.
        per_engine: dict[str, _EngineBucket] = {}
        total_usd_cents = Decimal("0")
        has_unpriced = False

        for r in records:
            bucket = per_engine.setdefault(r.analysis_type, _EngineBucket())
            bucket.calls += 1
            bucket.prompt_tokens += r.prompt_tokens
            bucket.completion_tokens += r.completion_tokens
            bucket.latency_total_ms += r.latency_ms
            bucket.last_call_at = r.created_at

            price = _resolve_price(r.model)
            if price is None:
                has_unpriced = True
                continue
            input_per_1m, output_per_1m = price
            # Cost in **USD cents** = price_per_1m_USD * 100 * tokens / 1M
            #                       = price_per_1m_USD * tokens / 10_000
            cost_cents = (
                input_per_1m * Decimal(r.prompt_tokens) / Decimal("10000")
                + output_per_1m * Decimal(r.completion_tokens) / Decimal("10000")
            )
            bucket.cost_usd_cents += cost_cents
            total_usd_cents += cost_cents

        engines: list[EngineUsage] = []
        for engine, bucket in sorted(per_engine.items()):
            avg_latency = (
                bucket.latency_total_ms // bucket.calls if bucket.calls else 0
            )
            engine_eur_cents = int(
                (
                    bucket.cost_usd_cents * Decimal(str(EUR_PER_USD))
                ).to_integral_value()
            )
            engines.append(
                EngineUsage(
                    engine=engine,
                    calls=bucket.calls,
                    prompt_tokens=bucket.prompt_tokens,
                    completion_tokens=bucket.completion_tokens,
                    cost_eur_cents=engine_eur_cents,
                    avg_latency_ms=avg_latency,
                    last_call_at=bucket.last_call_at,
                )
            )

        total_eur_cents = int((total_usd_cents * Decimal(str(EUR_PER_USD))).to_integral_value())

        return UsageSummary(
            user_id=str(user_id),
            period_label=period.label,
            period_start=period.start,
            period_end=period.end,
            total_calls=len(records),
            total_prompt_tokens=sum(r.prompt_tokens for r in records),
            total_completion_tokens=sum(r.completion_tokens for r in records),
            total_cost_eur_cents=total_eur_cents,
            has_unpriced_models=has_unpriced,
            engines=engines,
        )


# Re-export so ``from app.services.ai_usage_service import func, select``
# isn't a thing (the module purposely doesn't leak SQLAlchemy primitives
# upward — keep imports tidy).
__all__ = [
    "EUR_PER_USD",
    "AIUsageService",
    "EngineUsage",
    "UsagePeriod",
    "UsageSummary",
]

# Silence unused-import warning when the SQL helpers are pruned by ruff.
_ = (func, select)
