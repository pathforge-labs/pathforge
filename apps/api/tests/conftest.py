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
import warnings
from collections.abc import AsyncGenerator, Generator
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
from sqlalchemy.orm import ORMExecuteState
from sqlalchemy.orm import Session as _SyncSession
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
    type_: TypeEngine,
    compiler: Any,
    **kw: Any,
) -> str:
    return "TEXT"


# Vector → TEXT
@compiles(Vector, "sqlite")  # type: ignore[misc]
def _compile_vector_sqlite(
    type_: TypeEngine,
    compiler: Any,
    **kw: Any,
) -> str:
    return "TEXT"


# JSON → TEXT
@compiles(JSON, "sqlite")  # type: ignore[misc]
def _compile_json_sqlite(
    type_: TypeEngine,
    compiler: Any,
    **kw: Any,
) -> str:
    return "TEXT"


# PostgreSQL UUID → TEXT (SQLite stores as string representation)
@compiles(PG_UUID, "sqlite")  # type: ignore[misc]
def _compile_uuid_sqlite(
    type_: TypeEngine,
    compiler: Any,
    **kw: Any,
) -> str:
    return "TEXT"


# Patch UUID bind processor to accept both uuid.UUID and str values
# in SQLite. The default processor calls value.hex which fails on strings.
_original_uuid_bind = PG_UUID.bind_processor


def _patched_uuid_bind(
    self: PG_UUID,
    dialect: Dialect,
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
    self: PG_UUID,
    dialect: Dialect,
    coltype: Any,
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


# ── Email-verification bypass (F28 audit follow-up) ──────────────
#
# ``UserService.authenticate`` now rejects email-based accounts whose
# ``is_verified`` flag is still False. That is a production hardening
# (audit finding Sprint 39 → 28) but it would break the vast majority
# of existing tests, which follow a ``register → login`` pattern via
# HTTP endpoints and never mock the verify-email step.
#
# Rather than retrofit every test to call ``/verify-email`` (dozens of
# call sites), tests opt into a shared autouse fixture that
# transparently flips ``is_verified`` right before authentication.
# Tests that MUST see the unverified path (e.g. the guardrail test
# itself) mark themselves ``@pytest.mark.no_auto_verify`` and skip
# the shortcut.


@pytest.fixture(autouse=True)
def _auto_verify_on_login(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-verify email accounts before password authentication.

    Opt-out via ``@pytest.mark.no_auto_verify`` for tests that need to
    exercise the "unverified account is rejected" behaviour directly.
    """
    if request.node.get_closest_marker("no_auto_verify"):
        return

    from sqlalchemy import update as sql_update

    from app.models.user import User as UserModel
    from app.schemas.user import TokenResponse
    from app.services.user_service import UserService

    original_authenticate = UserService.authenticate

    async def _patched_authenticate(
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> TokenResponse:
        # Flip is_verified for any matching account before delegating to
        # the real authenticate() so that the verification gate becomes
        # a no-op for the register→login test pattern.
        await db.execute(
            sql_update(UserModel).where(UserModel.email == email).values(is_verified=True)
        )
        await db.flush()
        return await original_authenticate(db, email=email, password=password)

    monkeypatch.setattr(
        UserService,
        "authenticate",
        staticmethod(_patched_authenticate),
    )


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
            session_sync: Any,
            transaction_sync: Any,
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
async def registered_user(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    """Register a test user and mark them verified.

    F28 audit fix: login now requires ``is_verified=True`` for email
    accounts. Tests that use the ``auth_headers`` fixture (which logs in
    via HTTP) must therefore flip the flag after registration so the
    login call succeeds without exercising the full email-verification
    flow, which is covered by dedicated tests.
    """
    from sqlalchemy import update as sql_update

    from app.models.user import User as UserModel

    payload = {
        "email": "test@pathforge.eu",
        "password": "TestPass123!",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    # Verify the account so downstream login-based fixtures work.
    await db_session.execute(
        sql_update(UserModel).where(UserModel.email == payload["email"]).values(is_verified=True)
    )
    await db_session.commit()

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

    ``is_verified`` is True because integration tests using this fixture
    often go through the login endpoint, which requires verification
    (F28 audit fix).
    """
    from app.core.security import hash_password
    from app.models.user import User as UserModel

    user = UserModel(
        email="integration@pathforge.eu",
        hashed_password=hash_password("IntegrationPass123!"),
        full_name="Integration User",
        is_verified=True,
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
        MagicMock(
            side_effect=stripe.error.SignatureVerificationError(  # type: ignore[attr-defined]
                "Invalid signature",
                "sig_header",
            )
        ),
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


# ── P2-4: N+1 Lazy Load Detector ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def warn_on_lazy_load() -> Generator[None, None, None]:
    """Emit a warning for every SQLAlchemy lazy relationship load in tests.

    Detects N+1 patterns early: if a relationship is accessed without an
    explicit selectinload() or joinedload() in the parent query, SQLAlchemy
    will issue an additional SELECT.  This fixture surfaces those as
    UserWarning so they appear in pytest's warning summary.

    Runs automatically for every test.  To suppress for a specific test
    that intentionally uses lazy loading, use:
        @pytest.mark.filterwarnings("ignore:N+1 risk")
    """

    def _listener(orm_execute_state: ORMExecuteState) -> None:
        if (
            orm_execute_state.is_relationship_load
            and orm_execute_state.lazy_loaded_from is not None
        ):
            cls_name = orm_execute_state.lazy_loaded_from.mapper.class_.__name__
            warnings.warn(
                f"N+1 risk: lazy relationship load triggered from "
                f"{cls_name}. Add selectinload() or joinedload() to "
                "the parent query to prevent N+1 queries.",
                stacklevel=10,
            )

    event.listen(_SyncSession, "do_orm_execute", _listener, propagate=True)
    yield
    event.remove(_SyncSession, "do_orm_execute", _listener)


# ── T2 / Sprint 55 / ADR-0007: Query Budget enforcement ─────────
#
# When the QueryBudgetMiddleware is in place, every HTTP-driven test
# implicitly walks through it. This fixture supplements that with three
# guarantees the production middleware can't make:
#
#   * **Hard-fail mode** in tests: production logs a Sentry breadcrumo
#     on overage; tests fail outright so the regression never reaches
#     review.
#   * **Registry of declared routes**: every observed (endpoint, actual,
#     declared) tuple is captured for the test_query_budgets.py report
#     (CI artefact).
#   * **Inventory of unannotated routes**: every observed
#     (endpoint, actual) tuple for handlers WITHOUT
#     ``@route_query_budget`` is captured separately, so the rollout
#     PR (T2-rollout) can derive measured-p95 budgets from a single
#     suite run instead of guess-and-iterate.
#
# Tests that intentionally bypass should mark themselves with
# ``@pytest.mark.no_query_budget`` (see pyproject.toml).

#: Routes carrying ``@route_query_budget`` — entries are
#: ``{endpoint_qualname: (declared, max_observed)}``.
_query_budget_registry: dict[str, tuple[int, int]] = {}

#: Routes without an annotation — entries are
#: ``{endpoint_qualname: max_observed}``.  Populated by the autouse
#: fixture below; rendered separately by ``test_query_budgets.py`` so
#: the T2-rollout PR has a single source of truth for "what budget
#: should I declare for this route?"
_unannotated_query_observations: dict[str, int] = {}


def _record_query_budget_observation(
    *, endpoint_qualname: str, declared: int, observed: int
) -> None:
    prev_decl, prev_max = _query_budget_registry.get(endpoint_qualname, (declared, 0))
    if declared != prev_decl:  # pragma: no cover — invariant
        raise AssertionError(
            f"Inconsistent declared budget for {endpoint_qualname}: {prev_decl} vs {declared}"
        )
    _query_budget_registry[endpoint_qualname] = (
        declared,
        max(prev_max, observed),
    )


def _record_unannotated_observation(*, endpoint_qualname: str, observed: int) -> None:
    prev = _unannotated_query_observations.get(endpoint_qualname, 0)
    _unannotated_query_observations[endpoint_qualname] = max(prev, observed)


@pytest.fixture(scope="session", autouse=True)
def _ensure_query_counter_listener_registered() -> None:
    """Httpx's ``ASGITransport`` does not run FastAPI's ``lifespan``, so
    the SQL listener installed in ``app.main.lifespan`` never fires
    during tests.  Register it once per session so every test client
    walks through a fully-instrumented stack.

    Idempotent — subsequent calls (e.g. inside individual modules that
    also register at module scope) are no-ops.
    """
    from app.core.query_recorder import register_query_counter_listener

    register_query_counter_listener()


@pytest.fixture(autouse=True)
def _enforce_route_query_budgets(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Autouse: assert observed query count ≤ declared budget for every
    request issued during the test, record observations for both
    annotated and unannotated routes."""
    if request.node.get_closest_marker("no_query_budget") is not None:
        yield
        return

    from app.core.middleware import QueryBudgetMiddleware
    from app.core.query_budget import (
        NoQueryBudgetDeclaredError,
        get_route_query_budget,
    )

    original_dispatch = QueryBudgetMiddleware.dispatch
    test_qualname = request.node.nodeid

    async def _wrapped_dispatch(
        self: QueryBudgetMiddleware,
        starlette_request: Any,
        call_next: Any,
    ) -> Any:
        response = await original_dispatch(self, starlette_request, call_next)
        endpoint = getattr(starlette_request.scope.get("route"), "endpoint", None)
        if endpoint is None:
            return response
        # The middleware sets ``x-query-count`` only in non-prod, which
        # is the test environment.  Pull the count off the response.
        header = response.headers.get("x-query-count")
        if header is None:
            return response
        observed = int(header)
        try:
            declared = get_route_query_budget(endpoint)
        except NoQueryBudgetDeclaredError:
            # T2 rollout is complete — every production handler in
            # ``app/api/v1/`` MUST carry an explicit ``@route_query_budget``
            # so the per-route causality ledger has a meaningful upper
            # bound. Continue to capture the unannotated observation
            # (so the report still surfaces the offender) but enforce
            # the policy as a hard fail. Use ``@pytest.mark.no_query_budget``
            # to deliberately opt out of the gate for tests that exercise
            # legacy routes still pending measurement.
            _record_unannotated_observation(
                endpoint_qualname=endpoint.__qualname__,
                observed=observed,
            )
            raise AssertionError(
                f"Route handler '{endpoint.__qualname__}' is missing the "
                "@route_query_budget decorator. T2 rollout requires every "
                "handler in app/api/v1/ to declare a query budget. Add "
                f"@route_query_budget(max_queries={max(observed, 4)}) above "
                "the handler. Use @pytest.mark.no_query_budget to opt out."
            ) from None
        _record_query_budget_observation(
            endpoint_qualname=endpoint.__qualname__,
            declared=declared,
            observed=observed,
        )
        if observed > declared:
            raise AssertionError(
                f"Query budget exceeded in {test_qualname}: "
                f"{endpoint.__qualname__} ran {observed} queries, "
                f"declared {declared}. "
                "Either fix the N+1 or update the @route_query_budget "
                "annotation. Use @pytest.mark.no_query_budget to opt out."
            )
        return response

    QueryBudgetMiddleware.dispatch = _wrapped_dispatch  # type: ignore[method-assign]
    try:
        yield
    finally:
        QueryBudgetMiddleware.dispatch = original_dispatch  # type: ignore[method-assign]


@pytest.fixture
def query_budget_registry() -> dict[str, tuple[int, int]]:
    """Read-only snapshot of the per-endpoint budget registry."""
    return dict(_query_budget_registry)


@pytest.fixture
def unannotated_query_observations() -> dict[str, int]:
    """Read-only snapshot of the inventory-mode observations for
    handlers without a declared budget."""
    return dict(_unannotated_query_observations)
