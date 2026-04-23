"""
PathForge API — Test Configuration
====================================
Async test fixtures for FastAPI endpoint testing.

Uses SQLite (in-memory) for fast isolated tests.
Registers custom type compilers to handle PostgreSQL-specific
column types (ARRAY, Vector, JSON) that don't exist in SQLite.
"""

from __future__ import annotations

import asyncio
import uuid as _uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest
from httpx import ASGITransport, AsyncClient

# pgvector's Vector type
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.type_api import TypeEngine

if TYPE_CHECKING:
    from app.models.user import User


# ── SQLite ↔ PostgreSQL Type Compatibility ────────────────────
#
# We need to register compilation hooks BEFORE importing models,
# so that when Base.metadata.create_all runs, the types are known.


# ARRAY → TEXT (SQLite stores serialized representation)
@compiles(ARRAY, "sqlite")  # type: ignore[misc]
def _compile_array_sqlite(
    type_: TypeEngine, compiler: Any, **kw: Any,
) -> str:
    return "TEXT"


# Vector → TEXT
@compiles(Vector, "sqlite")  # type: ignore[misc]
def _compile_vector_sqlite(
    type_: TypeEngine, compiler: Any, **kw: Any,
) -> str:
    return "TEXT"


# JSON → TEXT
@compiles(JSON, "sqlite")  # type: ignore[misc]
def _compile_json_sqlite(
    type_: TypeEngine, compiler: Any, **kw: Any,
) -> str:
    return "TEXT"


# PostgreSQL UUID → TEXT (SQLite stores as string representation)
@compiles(PG_UUID, "sqlite")  # type: ignore[misc]
def _compile_uuid_sqlite(
    type_: TypeEngine, compiler: Any, **kw: Any,
) -> str:
    return "TEXT"


# Patch UUID bind processor to accept both uuid.UUID and str values
# in SQLite. The default processor calls value.hex which fails on strings.
_original_uuid_bind = PG_UUID.bind_processor


def _patched_uuid_bind(
    self: PG_UUID, dialect: Dialect,
) -> Any:
    """Return a processor that handles both UUID objects and strings."""
    if dialect.name == "sqlite":
        def process(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, _uuid.UUID):
                return str(value)
            return str(value)
        return process
    return _original_uuid_bind(self, dialect)


PG_UUID.bind_processor = _patched_uuid_bind  # type: ignore[method-assign]

# Also patch result_processor to convert TEXT back to uuid.UUID for SQLite
_original_uuid_result = PG_UUID.result_processor


def _patched_uuid_result(
    self: PG_UUID, dialect: Dialect, coltype: Any,
) -> Any:
    """Convert TEXT strings back to uuid.UUID objects for SQLite."""
    if dialect.name == "sqlite":
        if getattr(self, "as_uuid", False):
            def process(value: Any) -> _uuid.UUID | None:
                if value is not None:
                    return _uuid.UUID(str(value))
                return None
            return process
        return None  # Return raw string if as_uuid=False
    return _original_uuid_result(self, dialect, coltype)


PG_UUID.result_processor = _patched_uuid_result  # type: ignore[method-assign]


# ── Now import models (which triggers Base.metadata population) ──
from app.models.base import Base

# ── Test JWT Secrets (RFC 7518 §3.2 compliant) ───────────────
# PyJWT ≥ 2.10 raises InsecureKeyLengthWarning for HMAC keys < 32 bytes.
# Override settings with 32+ byte test-safe values to prevent warnings
# regardless of environment configuration.

_TEST_JWT_SECRET = "pathforge-test-jwt-secret-32bytes!"  # 34 bytes
_TEST_JWT_REFRESH = "pathforge-test-refresh-secret-32b!"  # 35 bytes


@pytest.fixture(autouse=True, scope="session")
def _override_jwt_secrets() -> None:
    """Ensure JWT secrets meet PyJWT minimum key length in all tests."""
    from app.core.config import settings

    object.__setattr__(settings, "jwt_secret", _TEST_JWT_SECRET)
    object.__setattr__(settings, "jwt_refresh_secret", _TEST_JWT_REFRESH)


@pytest.fixture(autouse=True, scope="session")
def _disable_turnstile() -> None:
    """Disable Turnstile CAPTCHA verification in all tests.

    Without this, tests that hit registration/login endpoints would fail
    with 400 when TURNSTILE_SECRET_KEY is set in the local .env.
    Setting the key to empty string triggers the skip-path in
    verify_turnstile_token().
    """
    from app.core.config import settings

    object.__setattr__(settings, "turnstile_secret_key", "")


@pytest.fixture(autouse=True, scope="session")
def _test_token_blacklist_fail_open() -> None:
    """Set token blacklist to fail-open in tests (no Redis available).

    Without Redis, the blacklist check raises an exception. In production
    fail-closed mode rejects all requests (503). Tests need fail-open so
    that authenticated endpoints are reachable.
    """
    from app.core.config import settings

    object.__setattr__(settings, "token_blacklist_fail_mode", "open")


@pytest.fixture(autouse=True, scope="session")
def _enable_oauth_providers() -> None:
    """Set OAuth client IDs so provider routes don't return 501.

    Without configured client IDs, the OAuth routes return
    501 Not Implemented before reaching the token verification
    logic (which tests mock).
    """
    from app.core.config import settings

    object.__setattr__(settings, "google_oauth_client_id", "test-google-client-id")
    object.__setattr__(settings, "microsoft_oauth_client_id", "test-microsoft-client-id")


# ── Hermetic settings environment (ADR-0001/0002) ─────────────
# Shared opt-in fixture for tests that build fresh `Settings(...)` instances
# and need ambient env vars (e.g. from the developer's shell or a `.env` file)
# to NOT bleed into kwargs. Tests opt in via:
#     pytestmark = pytest.mark.usefixtures("hermetic_settings_env")
#
# Intentionally NOT autouse — the vast majority of tests work with the
# module-level `settings` singleton and do not construct new Settings.
@pytest.fixture
def hermetic_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip env vars that would shadow explicit kwargs to `Settings(...)`.

    Extend this list whenever a new Settings-oriented test surface (SSL,
    secrets, rate limits, etc.) lands. Single source of truth so future
    additions cannot drift across per-file fixtures.
    """
    for name in (
        # Core environment selector
        "ENVIRONMENT",
        # JWT guards (Sprint 38 H3)
        "JWT_SECRET",
        "JWT_REFRESH_SECRET",
        # Database SSL (ADR-0001)
        "DATABASE_URL",
        "DATABASE_SSL",
        # Redis SSL (ADR-0002)
        "REDIS_URL",
        "REDIS_SSL",
    ):
        monkeypatch.delenv(name, raising=False)


# ── Test Database ─────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create an event loop for the test session.

    Note: This fixture is deprecated in pytest-asyncio >= 0.24 but still
    required for our session-scoped async fixtures (test_engine, etc.).
    Migration to loop_scope markers planned for a future sprint.
    """
    loop = asyncio.new_event_loop()
    yield loop  # type: ignore[misc]
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create a test database engine with all tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session that rolls back after each test."""
    # Use a connection-level transaction so each test is isolated
    async with test_engine.connect() as conn:
        transaction = await conn.begin()

        # Use a nested savepoint so session.commit() doesn't
        # finalize the outer transaction (avoids SAWarning)
        nested = await conn.begin_nested()

        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Restart nested savepoint after each session commit
        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_nested(
            session_sync: Any, transaction_sync: Any,
        ) -> None:
            nonlocal nested
            if not nested.is_active:
                nested = conn.sync_connection.begin_nested()  # type: ignore[union-attr]

        yield session

        await session.close()
        await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the test database."""
    from app.core.database import get_db
    from app.core.rate_limit import limiter
    from app.main import app

    # Reset rate limiter state between tests (Sprint 30)
    limiter.reset()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return their data."""
    payload = {
        "email": "test@pathforge.eu",
        "password": "TestPass123!",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return {**response.json(), "password": payload["password"]}


@pytest.fixture
async def auth_headers(client: AsyncClient, registered_user: dict[str, str]) -> dict[str, str]:
    """Login and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authenticated_user(db_session: AsyncSession) -> User:
    """Create a test user directly in the database and return the ORM object.

    Unlike ``registered_user``, this fixture bypasses HTTP endpoints,
    providing a deterministic User instance for integration tests that
    need an authenticated context without depending on the auth routes.
    """
    from app.core.security import hash_password
    from app.models.user import User as UserModel

    user = UserModel(
        email="integration@pathforge.eu",
        hashed_password=hash_password("IntegrationPass123!"),
        full_name="Integration User",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_client(
    client: AsyncClient,
    authenticated_user: User,
) -> AsyncClient:
    """Return an AsyncClient pre-configured with valid auth headers.

    Combines the ``client`` and ``authenticated_user`` fixtures to
    provide a ready-to-use authenticated HTTP client for integration
    tests targeting protected endpoints.
    """
    from app.core.security import create_access_token

    token = create_access_token(str(authenticated_user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ── Sprint 35: Stripe Mock Fixtures (TI1) ───────────────────


@pytest.fixture
def mock_stripe(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock Stripe SDK to prevent real API calls during testing.

    Returns a dict of mock objects keyed by Stripe resource type,
    allowing assertions on calls made to the Stripe API.
    """
    from unittest.mock import MagicMock

    mock_customer = MagicMock()
    mock_customer.id = "cus_test123"
    mock_customer.email = "test@pathforge.eu"

    mock_checkout_session = MagicMock()
    mock_checkout_session.url = "https://checkout.stripe.com/test-session"
    mock_checkout_session.id = "cs_test123"

    mock_portal_session = MagicMock()
    mock_portal_session.url = "https://billing.stripe.com/portal/test-session"

    mock_subscription = MagicMock()
    mock_subscription.id = "sub_test123"
    mock_subscription.status = "active"
    mock_subscription.current_period_start = 1700000000
    mock_subscription.current_period_end = 1702592000

    # Patch stripe module
    import stripe

    monkeypatch.setattr(stripe, "api_key", "sk_test_fake")
    monkeypatch.setattr(
        stripe.checkout.Session,
        "create",
        MagicMock(return_value=mock_checkout_session),
    )
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        MagicMock(return_value=mock_portal_session),
    )
    monkeypatch.setattr(
        stripe.Customer,
        "create",
        MagicMock(return_value=mock_customer),
    )
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        MagicMock(side_effect=stripe.error.SignatureVerificationError(  # type: ignore[attr-defined]
            "Invalid signature", "sig_header",
        )),
    )

    return {
        "customer": mock_customer,
        "checkout_session": mock_checkout_session,
        "portal_session": mock_portal_session,
        "subscription": mock_subscription,
    }


@pytest.fixture
async def billing_test_user(
    db_session: AsyncSession,
    authenticated_user: User,
) -> User:
    """Create a test user with a pre-existing subscription for billing tests.

    Reuses the authenticated_user fixture and adds a subscription record,
    providing a ready-made user for billing endpoint testing (AC5).
    """
    from app.models.subscription import Subscription

    subscription = Subscription(
        user_id=authenticated_user.id,
        tier="free",
        status="active",
        stripe_customer_id="cus_test123",
    )
    db_session.add(subscription)
    await db_session.flush()
    await db_session.refresh(authenticated_user)
    return authenticated_user


# ── Sprint Pre-40: OAuth Test Fixtures (H7) ─────────────────


@pytest.fixture
async def oauth_user(db_session: AsyncSession) -> User:
    """Create an OAuth-registered user (Google, no password, verified).

    Provides a user that was created via Google OAuth — has no password
    and is pre-verified. Used for OAuth login and account-linking tests.
    """
    from app.models.user import User as UserModel

    user = UserModel(
        email="oauth@google.test",
        hashed_password=None,
        full_name="OAuth User",
        auth_provider="google",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive user for access-denied tests.

    Provides a deactivated user to verify 403 guards on OAuth
    and standard auth endpoints.
    """
    from app.core.security import hash_password
    from app.models.user import User as UserModel

    user = UserModel(
        email="inactive@pathforge.eu",
        hashed_password=hash_password("InactivePass123!"),
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user

