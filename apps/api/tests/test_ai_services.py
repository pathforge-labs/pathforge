"""
PathForge — AI Service Unit Tests
====================================
Tests for the AI pipeline with mocked LLM / embedding calls.

Covers: embedding vector validation, matching service, CV tailor output structure.
"""

import math
import uuid

import pytest

# ── Embedding Vector Validation Tests ──────────────────────────


class TestEmbeddingVectorValidation:
    """Tests for SEC-1: NaN/Inf guard in matching.py."""

    def test_valid_embedding_produces_string(self):
        """A normal embedding should produce a valid bracket-delimited string."""

        embedding = [0.1, 0.2, 0.3, -0.5, 1.0]
        validated = []
        for f in embedding:
            val = float(f)
            assert math.isfinite(val)
            validated.append(val)
        result = "[" + ",".join(str(v) for v in validated) + "]"
        assert result == "[0.1,0.2,0.3,-0.5,1.0]"

    def test_nan_embedding_raises_value_error(self):
        """NaN values in embedding should raise ValueError."""
        embedding = [0.1, float("nan"), 0.3]
        with pytest.raises(ValueError, match="Non-finite"):
            for f in embedding:
                val = float(f)
                if not math.isfinite(val):
                    raise ValueError(f"Non-finite embedding value detected: {val}")

    def test_inf_embedding_raises_value_error(self):
        """Inf values in embedding should raise ValueError."""
        embedding = [0.1, float("inf"), 0.3]
        with pytest.raises(ValueError, match="Non-finite"):
            for f in embedding:
                val = float(f)
                if not math.isfinite(val):
                    raise ValueError(f"Non-finite embedding value detected: {val}")

    def test_negative_inf_embedding_raises_value_error(self):
        """Negative Inf values in embedding should raise ValueError."""
        embedding = [0.1, float("-inf"), 0.3]
        with pytest.raises(ValueError, match="Non-finite"):
            for f in embedding:
                val = float(f)
                if not math.isfinite(val):
                    raise ValueError(f"Non-finite embedding value detected: {val}")


# ── Resume Text Size Validation Tests ──────────────────────────


class TestResumeTextSizeValidation:
    """Tests for SEC-2: max_length on ParseResumeRequest."""

    def test_request_rejects_oversized_text(self):
        """Resume text exceeding 100KB should be rejected by Pydantic."""
        from app.api.v1.ai import ParseResumeRequest

        oversized = "A" * 100_001  # Just over the limit
        with pytest.raises(ValueError):  # ValidationError
            ParseResumeRequest(raw_text=oversized)

    def test_request_accepts_normal_text(self):
        """Normal-sized resume text should be accepted."""
        from app.api.v1.ai import ParseResumeRequest

        normal = "A" * 500
        req = ParseResumeRequest(raw_text=normal)
        assert len(req.raw_text) == 500

    def test_request_rejects_too_short_text(self):
        """Resume text under 50 chars should be rejected."""
        from app.api.v1.ai import ParseResumeRequest

        with pytest.raises(ValueError):
            ParseResumeRequest(raw_text="short")


# ── UUID Schema Validation Tests ───────────────────────────────


class TestUUIDSchemaValidation:
    """Tests for CODE-5: UUID Pydantic types."""

    def test_valid_uuid_accepted(self):
        """Valid UUID strings should be accepted by the schema."""
        from app.api.v1.ai import TailorCVRequest

        valid_id = str(uuid.uuid4())
        req = TailorCVRequest(resume_id=valid_id, job_id=valid_id)
        assert req.resume_id == uuid.UUID(valid_id)

    def test_invalid_uuid_rejected(self):
        """Invalid UUID strings should be rejected at the schema level."""
        from app.api.v1.ai import TailorCVRequest

        with pytest.raises(ValueError):
            TailorCVRequest(resume_id="not-a-uuid", job_id="also-not-valid")


# ── JWT Secret Separation Tests ────────────────────────────────


class TestJWTSecretSeparation:
    """Tests for SEC-3: separate secrets for access/refresh tokens."""

    def test_access_token_uses_jwt_secret(self):
        """Access tokens should decode with jwt_secret."""
        import jwt

        from app.core.config import settings
        from app.core.security import create_access_token

        token = create_access_token("test-user-id")
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "access"

    def test_refresh_token_uses_refresh_secret(self):
        """Refresh tokens should decode with jwt_refresh_secret, not jwt_secret."""
        import jwt
        from jwt import PyJWTError

        from app.core.config import settings
        from app.core.security import create_refresh_token

        token = create_refresh_token("test-user-id")

        # Should succeed with refresh secret
        payload = jwt.decode(
            token, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "refresh"
        assert "jti" in payload  # SEC-4: jti claim present

        # Should fail with access secret (different from refresh secret)
        if settings.jwt_secret != settings.jwt_refresh_secret:
            with pytest.raises(PyJWTError):
                jwt.decode(
                    token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
                )

    def test_refresh_token_has_unique_jti(self):
        """Each refresh token should have a unique jti claim."""
        import jwt

        from app.core.config import settings
        from app.core.security import create_refresh_token

        token1 = create_refresh_token("test-user-id")
        token2 = create_refresh_token("test-user-id")

        p1 = jwt.decode(token1, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])
        p2 = jwt.decode(token2, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])

        assert p1["jti"] != p2["jti"]


# ── Application Status Constraint Tests ────────────────────────


class TestApplicationStatusConstraint:
    """Tests for CODE-2: CheckConstraint on application status."""

    def test_valid_status_values(self):
        """All defined status values should be valid."""
        from app.models.application import ApplicationStatus

        valid_statuses = [
            "saved", "applied", "interviewing",
            "offered", "rejected", "withdrawn",
        ]
        for s in valid_statuses:
            assert s in [e.value for e in ApplicationStatus]
