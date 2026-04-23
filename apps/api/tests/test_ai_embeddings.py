"""
PathForge AI Engine — Embedding Service Tests
================================================
Tests for canonical text generation, embedding service, and batch logic.
All tests use mocked Voyage AI client — no API keys needed.
Includes circuit breaker integration tests (ADR-0003 verification criteria).
"""

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.ai.embeddings import EmbeddingService
from app.ai.schemas import ParsedEducation, ParsedExperience, ParsedResume, ParsedSkill

# ── Canonical Text Generation Tests ────────────────────────────


class TestCanonicalText:
    """Test the canonical text generation for resumes and jobs."""

    def test_resume_canonical_full(self):
        """Full resume should produce a well-structured canonical text."""
        resume = ParsedResume(
            full_name="Alice Engineer",
            summary="Full-stack developer with 8 years experience.",
            skills=[
                ParsedSkill(name="Python"),
                ParsedSkill(name="React"),
                ParsedSkill(name="PostgreSQL"),
            ],
            experience=[
                ParsedExperience(
                    company="TechCo",
                    title="Senior Developer",
                    description="Built scalable APIs",
                    achievements=["Reduced latency by 40%"],
                ),
            ],
            education=[
                ParsedEducation(
                    institution="MIT",
                    degree="MSc",
                    field="Computer Science",
                ),
            ],
        )

        canonical = EmbeddingService._resume_to_canonical(resume)

        assert "Full-stack developer" in canonical
        assert "Python" in canonical
        assert "React" in canonical
        assert "Senior Developer at TechCo" in canonical
        assert "Reduced latency by 40%" in canonical
        assert "MSc in Computer Science from MIT" in canonical

    def test_resume_canonical_empty(self):
        """Empty resume should produce a fallback string."""
        resume = ParsedResume()
        canonical = EmbeddingService._resume_to_canonical(resume)
        assert canonical == "No resume information available"

    def test_resume_canonical_skills_only(self):
        """Resume with only skills should still produce valid text."""
        resume = ParsedResume(
            skills=[ParsedSkill(name="Rust"), ParsedSkill(name="Go")],
        )
        canonical = EmbeddingService._resume_to_canonical(resume)
        assert "Skills: Rust, Go" in canonical

    def test_job_canonical_full(self):
        """Full job listing should produce structured canonical text."""
        canonical = EmbeddingService._job_to_canonical(
            title="Backend Engineer",
            company="Startup Inc",
            description="Build high-performance APIs using Python and PostgreSQL.",
        )
        assert "Job Title: Backend Engineer" in canonical
        assert "Company: Startup Inc" in canonical
        assert "Build high-performance APIs" in canonical

    def test_job_canonical_no_description(self):
        """Job without description should still produce valid text."""
        canonical = EmbeddingService._job_to_canonical(
            title="Designer",
            company="DesignCo",
            description="",
        )
        assert "Job Title: Designer" in canonical
        assert "Company: DesignCo" in canonical
        assert "Description" not in canonical


# ── Embedding Service Tests (with mocked Voyage client) ────────


class TestEmbeddingService:
    """Test EmbeddingService with mocked Voyage AI client."""

    def _create_mock_client(self, dim: int = 3072) -> MagicMock:
        """Create a mock Voyage AI client that returns fake embeddings."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * dim]

        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result
        return mock_client

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Should embed a single text and return vector of correct dimensions."""
        service = EmbeddingService(api_key="test-key")
        mock_client = self._create_mock_client()
        service._client = mock_client

        result = await service.embed_text("Hello world")

        assert len(result) == 3072
        assert all(isinstance(v, float) for v in result)
        mock_client.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_text_empty_raises(self):
        """Should raise ValueError for empty text."""
        service = EmbeddingService(api_key="test-key")

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            await service.embed_text("")

    @pytest.mark.asyncio
    async def test_embed_batch_success(self):
        """Should embed multiple texts and return list of vectors."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 3072, [0.2] * 3072, [0.3] * 3072]

        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result

        service = EmbeddingService(api_key="test-key")
        service._client = mock_client

        results = await service.embed_batch(["text1", "text2", "text3"])

        assert len(results) == 3
        assert len(results[0]) == 3072

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self):
        """Should return empty list for empty input."""
        service = EmbeddingService(api_key="test-key")
        results = await service.embed_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_embed_batch_chunking(self):
        """Should chunk large batches to respect API limits."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 3072]

        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result

        service = EmbeddingService(api_key="test-key")
        service._client = mock_client
        service._batch_size = 2  # Small batch for testing

        texts = ["text1", "text2", "text3", "text4", "text5"]
        await service.embed_batch(texts)

        # With batch_size=2, 5 texts should produce 3 API calls
        assert mock_client.embed.call_count == 3

    @pytest.mark.asyncio
    async def test_embed_resume(self):
        """Should generate canonical text from resume and embed it."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.5] * 3072]

        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result

        service = EmbeddingService(api_key="test-key")
        service._client = mock_client

        resume = ParsedResume(
            summary="Expert developer",
            skills=[ParsedSkill(name="Python")],
        )

        result = await service.embed_resume(resume)

        assert len(result) == 3072
        # Verify the canonical text was passed to the embed call
        call_args = mock_client.embed.call_args
        texts_arg = call_args.kwargs.get("texts") or call_args[1].get("texts")
        assert "Expert developer" in texts_arg[0]
        assert "Python" in texts_arg[0]

    @pytest.mark.asyncio
    async def test_embed_job(self):
        """Should generate canonical text from job listing and embed it."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.3] * 3072]

        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result

        service = EmbeddingService(api_key="test-key")
        service._client = mock_client

        result = await service.embed_job(
            title="Senior Engineer",
            company="TechCo",
            description="Build scalable systems",
        )

        assert len(result) == 3072
        call_args = mock_client.embed.call_args
        texts_arg = call_args.kwargs.get("texts") or call_args[1].get("texts")
        assert "Senior Engineer" in texts_arg[0]


# ── ADR-0003 Verification: Circuit Breaker Integration ────────────────────────


class _FakeRedis:
    def __init__(self, state: str = "open", failures: int = 3, opened_at: float | None = None) -> None:
        self._store: dict[str, str] = {
            "state": state,
            "failures": str(failures),
            "opened_at": str(opened_at or time.time()),
        }

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._store)

    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        self._store.update({k: str(v) for k, v in mapping.items()})
        return 1

    async def expire(self, key: str, ttl: int) -> bool:
        return True


class TestEmbeddingCircuitBreaker:
    """Verify ADR-0003: circuit breaker wired into EmbeddingService."""

    @pytest.mark.asyncio
    async def test_embed_text_raises_runtime_error_when_circuit_open(self) -> None:
        """Open circuit on embed_text should raise RuntimeError (not CircuitOpenError)."""
        service = EmbeddingService(api_key="test-key")
        service._breaker._redis = _FakeRedis(state="open", failures=3)  # type: ignore[assignment]

        with pytest.raises(RuntimeError, match="Voyage AI embedding service unavailable"):
            await service.embed_text("some text")

    @pytest.mark.asyncio
    async def test_embed_batch_raises_runtime_error_when_circuit_open(self) -> None:
        """Open circuit on embed_batch should raise RuntimeError."""
        service = EmbeddingService(api_key="test-key")
        service._breaker._redis = _FakeRedis(state="open", failures=3)  # type: ignore[assignment]

        with pytest.raises(RuntimeError, match="Voyage AI embedding service unavailable"):
            await service.embed_batch(["text1", "text2"])

    @pytest.mark.asyncio
    async def test_embed_text_fail_open_proceeds_when_redis_unavailable(self) -> None:
        """When Redis is unavailable, embed_text should proceed without circuit protection."""
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 3072]
        mock_client = MagicMock()
        mock_client.embed.return_value = mock_result

        service = EmbeddingService(api_key="test-key")
        service._client = mock_client

        async def _redis_error(*_: Any, **__: Any) -> None:
            raise ConnectionError("Redis not provisioned (OPS-4)")

        service._breaker._redis = _FakeRedis(state="closed")  # type: ignore[assignment]
        service._breaker._redis.hgetall = _redis_error  # type: ignore[method-assign]

        result = await service.embed_text("hello world")

        assert len(result) == 3072
        mock_client.embed.assert_called_once()
