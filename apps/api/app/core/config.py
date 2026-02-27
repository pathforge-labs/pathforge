"""
PathForge API — Career Intelligence Platform
==========================================
Core application configuration.

All settings are loaded from environment variables with sensible defaults.
Import from here, never hardcode configuration values.

Usage:
    from app.core.config import settings
    from app.core.config import EMBEDDING_DIM
"""

# ── Module Constants (compile-time, not runtime-configurable) ────────
# Changing EMBEDDING_DIM requires re-embedding ALL vectors + index rebuild.
# This is intentionally NOT a settings field — it must match the Voyage AI
# model output dimension and the pgvector column definition.
EMBEDDING_DIM: int = 3072

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Brand Identity ──────────────────────────────────────────
    app_name: str = "PathForge"
    app_slug: str = "pathforge"
    app_tagline: str = "Career Intelligence for Everyone"
    app_version: str = "0.1.0"

    # ── Server ──────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"  # Sprint 30: environment-configurable log level

    # ── Database ────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pathforge_dev"
    database_echo: bool = False
    database_pool_recycle: int = 3600   # Prevent stale connections (seconds)
    database_pool_timeout: int = 30     # Max wait for pool connection (seconds)
    database_ssl: bool = False          # Enable for Supabase production

    # ── Redis ───────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_ssl: bool = False
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5

    # ── JWT Authentication ──────────────────────────────────────
    jwt_secret: str = "change-me-in-production-use-a-real-secret"
    jwt_refresh_secret: str = "change-me-refresh-secret-must-differ"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── CORS ────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    cors_origins_production: list[str] = [
        "https://pathforge.eu",
        "https://www.pathforge.eu",
    ]

    # ── AI / LLM Providers ─────────────────────────────────────
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    voyage_api_key: str = ""

    # ── LiteLLM Tiered Model Routing ─────────────────────────
    # Models are tier-based and swappable via env without code changes.
    # Primary (80%): workhorse for CV gen, match explanations
    # Fast (15%): high-volume parsing, classification
    # Deep (5%): complex career DNA analysis only
    llm_primary_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_fast_model: str = "gemini/gemini-2.0-flash"
    llm_deep_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_timeout: int = 60
    llm_max_retries: int = 3

    # ── LLM Production Routing (Sprint 29) ────────────────────
    llm_monthly_budget_usd: float = 200.0   # Redis-backed monthly budget guard
    llm_primary_rpm: int = 60               # Requests per minute — Primary tier
    llm_fast_rpm: int = 200                 # Requests per minute — Fast tier
    llm_deep_rpm: int = 10                  # Requests per minute — Deep tier

    # ── LLM Observability (Langfuse) ────────────────────────
    # Disabled by default — zero overhead until explicitly enabled.
    # Self-hostable: set langfuse_host to your own instance.
    llm_observability_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_sampling_rate: float = 0.1     # 10% sampling in production
    langfuse_pii_redaction: bool = True     # Redact PII before sending traces

    # ── Voyage AI Embeddings ─────────────────────────────────
    voyage_model: str = "voyage-3"
    voyage_embed_batch_size: int = 128

    # ── Rate Limiting ────────────────────────────────────────────
    # Per-user limits on expensive AI endpoints (req/minute)
    rate_limit_parse: str = "30/minute"
    rate_limit_embed: str = "20/minute"
    rate_limit_match: str = "30/minute"
    rate_limit_tailor: str = "10/minute"
    rate_limit_career_dna: str = "3/minute"
    rate_limit_ai_health: str = "30/minute"
    rate_limit_ai_analyses: str = "20/minute"
    ratelimit_storage_uri: str = "memory://"

    # ── Auth Rate Limits (Sprint 30) ─────────────────────────────
    rate_limit_login: str = "5/minute"       # Brute-force protection
    rate_limit_register: str = "3/minute"    # Registration abuse prevention
    rate_limit_refresh: str = "10/minute"    # Token refresh protection
    rate_limit_global_default: str = "200/minute"  # Configurable global default

    # ── Sentry Error Tracking (Sprint 30) ────────────────────────
    sentry_dsn: str = ""                    # Empty = disabled, zero overhead
    sentry_traces_sample_rate: float = 1.0  # Start 100%, dial to 0.1 after baseline week
    sentry_environment: str = ""            # Defaults to `environment` if empty
    sentry_release: str = ""                # Defaults to app_version if empty

    # ── Security Disclosure ──────────────────────────────────────
    security_contact_email: str = "security@pathforge.eu"
    security_txt_expires_days: int = 365

    # ── Job Aggregation Providers ────────────────────────────────
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jooble_api_key: str = ""
    aggregation_cron_hours: str = "{0, 6, 12, 18}"  # 4× daily cron schedule
    aggregation_batch_size: int = 100
    embedding_daily_limit: int = 1000               # Max jobs embedded per day (cost guard)

    # ── Worker Pool (Sprint 30) ─────────────────────────────────
    worker_max_jobs: int = 10              # Max concurrent jobs per worker
    worker_max_burst_jobs: int = 2         # Max burst jobs above max_jobs

    # ── Email Delivery (Resend) ──────────────────────────────────
    resend_api_key: str = ""
    digest_email_enabled: bool = False
    digest_from_email: str = "notifications@pathforge.eu"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def effective_cors_origins(self) -> list[str]:
        """Return CORS origins appropriate for the current environment."""
        if self.is_production:
            return self.cors_origins_production
        return self.cors_origins


settings = Settings()
