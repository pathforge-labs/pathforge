"""
PathForge AI Engine — Embedding Service
=========================================
Voyage AI v4 embedding generation for resumes and job listings.

Generates 3072-dimensional vectors that are stored in pgvector
and used for cosine similarity matching.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import voyageai

from app.ai.schemas import ParsedResume
from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings
from app.core.redis_ssl import resolve_redis_url

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate text embeddings using Voyage AI.

    Design decisions:
    - Singleton-like client (created per service instance)
    - Canonical text generation: structured resume → single embedding-ready string
    - Batch embedding with chunking (respects Voyage API limits)
    - Retry logic delegated to the Voyage AI SDK's built-in retries
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.voyage_api_key
        self._model = model or settings.voyage_model
        self._batch_size = settings.voyage_embed_batch_size

        if not self._api_key:
            logger.warning(
                "Voyage AI API key not configured. "
                "Set VOYAGE_API_KEY env var to enable embeddings."
            )
        self._client: Any = None
        self._breaker = CircuitBreaker(
            name="voyage",
            redis_url=resolve_redis_url(
                settings.redis_url,
                settings.redis_ssl_enabled,
                settings.environment,
            ),
        )

    def _get_client(self) -> Any:
        """Lazy-initialize the Voyage AI client."""
        if self._client is None:
            self._client = voyageai.Client(api_key=self._api_key)  # type: ignore[attr-defined]
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        start = time.monotonic()
        client = self._get_client()
        try:
            async with self._breaker:
                result = await asyncio.to_thread(
                    client.embed,
                    texts=[text],
                    model=self._model,
                    input_type="document",
                )
        except CircuitOpenError as exc:
            raise RuntimeError(f"Voyage AI embedding service unavailable: {exc}") from exc
        elapsed = time.monotonic() - start
        dim = len(result.embeddings[0])
        logger.info("Embedded 1 text (%d dims) in %.2fs", dim, elapsed)
        return list(result.embeddings[0])

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Automatically chunks into batches of `voyage_embed_batch_size`
        to respect API rate limits.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        client = self._get_client()
        start = time.monotonic()

        try:
            for i in range(0, len(texts), self._batch_size):
                chunk = texts[i : i + self._batch_size]
                async with self._breaker:
                    result = await asyncio.to_thread(
                        client.embed,
                        texts=chunk,
                        model=self._model,
                        input_type="document",
                    )
                all_embeddings.extend(result.embeddings)
        except CircuitOpenError as exc:
            raise RuntimeError(f"Voyage AI embedding service unavailable: {exc}") from exc

        elapsed = time.monotonic() - start
        logger.info(
            "Embedded %d texts in %d batches (%.2fs)",
            len(texts),
            (len(texts) + self._batch_size - 1) // self._batch_size,
            elapsed,
        )
        return all_embeddings

    async def embed_resume(self, parsed: ParsedResume) -> list[float]:
        """
        Create a canonical text representation of a parsed resume, then embed it.

        The canonical text is carefully structured to emphasize the most
        matching-relevant information for semantic similarity.

        Args:
            parsed: A ParsedResume from the resume parser.

        Returns:
            Embedding vector for the resume.
        """
        canonical = self._resume_to_canonical(parsed)
        return await self.embed_text(canonical)

    async def embed_job(
        self,
        title: str,
        company: str,
        description: str,
    ) -> list[float]:
        """
        Create a canonical text representation of a job listing, then embed it.

        Args:
            title: Job title.
            company: Company name.
            description: Job description text.

        Returns:
            Embedding vector for the job listing.
        """
        canonical = self._job_to_canonical(title, company, description)
        return await self.embed_text(canonical)

    # ── Canonical Text Generation ──────────────────────────────

    @staticmethod
    def _resume_to_canonical(parsed: ParsedResume) -> str:
        """
        Convert a ParsedResume into a canonical text for embedding.

        Structure: summary → skills → experience → education
        This ordering emphasizes the most matching-relevant fields first.
        """
        parts: list[str] = []

        if parsed.summary:
            parts.append(f"Professional Summary: {parsed.summary}")

        if parsed.skills:
            skill_names = [s.name for s in parsed.skills]
            parts.append(f"Skills: {', '.join(skill_names)}")

        for exp in parsed.experience:
            exp_text = f"{exp.title} at {exp.company}"
            if exp.description:
                exp_text += f". {exp.description}"
            if exp.achievements:
                exp_text += ". Achievements: " + "; ".join(exp.achievements)
            parts.append(exp_text)

        for edu in parsed.education:
            edu_text = f"{edu.degree} in {edu.field} from {edu.institution}"
            parts.append(edu_text)

        if parsed.certifications:
            cert_names = [c.name for c in parsed.certifications]
            parts.append(f"Certifications: {', '.join(cert_names)}")

        return "\n".join(parts) if parts else "No resume information available"

    @staticmethod
    def _job_to_canonical(title: str, company: str, description: str) -> str:
        """
        Convert job listing fields into a canonical text for embedding.

        Structure: title + company → full description
        """
        parts: list[str] = [f"Job Title: {title}", f"Company: {company}"]
        if description:
            parts.append(f"Description: {description}")
        return "\n".join(parts)
