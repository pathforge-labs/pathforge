"""
PathForge API — Observability Routes
==========================================
LLM metrics and platform health observability endpoints.

Sprint 20 — Hardening & Observability
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.llm_observability import get_collector
from app.models.user import User

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/llm-metrics")
async def get_llm_metrics(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get aggregated LLM usage metrics.

    Returns in-memory metrics including:
    - Global totals (calls, success rate, latency, tokens)
    - Per-model breakdown
    - Per-tier breakdown (primary/fast/deep)
    - Error type distribution

    Metrics reset on application restart. For persistent tracing,
    enable Langfuse via LLM_OBSERVABILITY_ENABLED=true.
    """
    return get_collector().get_metrics()
