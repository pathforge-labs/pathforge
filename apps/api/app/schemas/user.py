"""
PathForge — Pydantic Schemas for User & Auth
==============================================
Request/response DTOs for authentication and user management.
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Auth Schemas ────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    invite_token: str | None = Field(default=None, max_length=64)  # F17: backward compatible
    turnstile_token: str | None = Field(default=None)  # F19/F20: Turnstile CAPTCHA

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        """Enforce OWASP-aligned password complexity rules."""
        errors: list[str] = []
        if not re.search(r"[A-Z]", value):
            errors.append("one uppercase letter")
        if not re.search(r"\d", value):
            errors.append("one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/'`~;]", value):
            errors.append("one special character")
        if errors:
            missing = ", ".join(errors)
            msg = f"Password must contain at least {missing}"
            raise ValueError(msg)
        return value


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── User Schemas ────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    auth_provider: str
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


# ── Sprint 39: Password Reset & Email Verification ──────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        """Enforce OWASP-aligned password complexity rules (reuses register logic)."""
        errors: list[str] = []
        if not re.search(r"[A-Z]", value):
            errors.append("one uppercase letter")
        if not re.search(r"\d", value):
            errors.append("one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\\/'`~;]", value):
            errors.append("one special character")
        if errors:
            missing = ", ".join(errors)
            msg = f"Password must contain at least {missing}"
            raise ValueError(msg)
        return value


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class MessageResponse(BaseModel):
    """Generic message response for endpoints that don't return data."""
    message: str

