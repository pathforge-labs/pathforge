"""
PathForge — Push Token Schemas
================================
Pydantic request/response schemas for push token management.

Request Schemas:
    PushTokenRegister       — Register a device push token
    PushTokenDeregister     — Remove a device push token

Response Schemas:
    PushTokenStatusResponse — Push token registration status
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Request Schemas ────────────────────────────────────────────


class PushTokenRegister(BaseModel):
    """Register a device push token."""

    token: str = Field(
        ..., min_length=1, max_length=512,
        description="Expo push token (ExponentPushToken[...]).",
    )
    platform: Literal["ios", "android"] = Field(
        ..., description="Device platform.",
    )


class PushTokenDeregister(BaseModel):
    """Deregister the current device push token."""

    token: str = Field(
        ..., min_length=1, max_length=512,
        description="Token to deregister.",
    )


# ── Response Schemas ───────────────────────────────────────────


class PushTokenStatusResponse(BaseModel):
    """Push token registration status.

    Note: ``token`` returns a masked value (``***xxxx``)
    for PII protection. Full token is never exposed via API.
    """

    registered: bool
    token: str | None = None
    platform: str | None = None
