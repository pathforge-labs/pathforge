# PathForge — Code Review Style Guide

> This style guide instructs Gemini Code Assist on PathForge-specific coding
> standards and architectural conventions. Apply these rules when reviewing
> pull requests.

## Project Overview

PathForge is an AI-powered career intelligence platform built as a
**pnpm monorepo** with the following structure:

- `apps/api/` — Python 3.12+ FastAPI backend
- `apps/web/` — Next.js 15 (App Router) frontend
- `apps/mobile/` — React Native / Expo SDK 52 mobile app
- `packages/shared/` — Shared TypeScript types across web and mobile

## Python Standards (Backend — `apps/api/`)

### Type Safety

- **STRICT type hints** on all function signatures and return types.
- No untyped parameters. No `Any` unless unavoidable (document why).
- Use `Pydantic` models with `ConfigDict(from_attributes=True)` for all
  request/response schemas.
- **Confidence caps — two architecturally distinct categories.** Do not
  conflate them when reviewing.
  1. **Semantic confidence** (what the LLM claims about the *output
     content* — e.g. career-DNA skill-level, salary-range estimate,
     credential-mapping score) is **capped at 0.85** via the
     `MAX_*_CONFIDENCE` constants (`MAX_PASSPORT_CONFIDENCE`,
     `MAX_PLAN_CONFIDENCE`, `MAX_PC_CONFIDENCE`, etc.). DB CHECK
     constraints enforce `confidence <= 0.85` on these columns.
     Reviews must flag any LLM-output schema with `le > 0.85`.
  2. **Pipeline-execution confidence** (how reliably the AI pipeline
     itself ran — derived from observable telemetry: tier, retries,
     latency, token utilisation) is **capped at 0.95** via
     `app/core/llm_observability.py::CONFIDENCE_CAP`. This is a
     telemetry signal, not a claim about the output content; the
     0.95 cap is intentional ("never claim 100 % confidence" without
     suppressing the pipeline-health signal at 0.85). The schema
     `app/schemas/ai_transparency.py::AnalysisTransparency.confidence_score`
     documents `0.0–0.95, never 100 %`. Do **not** flag this as a
     styleguide violation.

### Naming & Style

- `snake_case` for variables and functions.
- `PascalCase` for classes.
- `SCREAMING_SNAKE_CASE` for constants.
- f-strings preferred over `.format()` or `%`.
- Maximum **800 lines per file**, **50 lines per function**,
  **4 levels of nesting**.

### Linting & Formatting

- **Ruff** is the sole linter and formatter — flag anything Ruff would catch.
- Import order: stdlib → third-party → local application.

### Security

- All LLM inputs **must** pass through `sanitize_user_text()` (OWASP LLM01).
- No hardcoded secrets — use environment variables via `app/core/config.py`.
- SQL injection prevention: always use SQLAlchemy ORM, never raw SQL strings.
- Rate limiting required on all public and AI-powered endpoints (`slowapi`).

### Error Handling

- **LLM calls** use the tiered fallback chain: Deep → Primary → Fast.
  If all tiers fail, raise `LLMError` — caught by `llm_error_handler` (503).
- Never swallow exceptions silently. Use `logger.exception()` for unexpected
  errors and structured `logger.warning()` for degraded-mode fallbacks.
- Circuit breaker pattern (`app/core/circuit_breaker.py`) for external APIs
  (Adzuna, Jooble, Voyage AI). Redis-backed state: CLOSED → OPEN → HALF_OPEN.
- Dead letter queue (`worker.py`) for ARQ jobs that exhaust all retries.

### Testing

- `pytest` with `@pytest.mark.asyncio` for async tests.
- Test files must mirror source structure: `tests/test_<module>.py`.
- All new endpoints need corresponding test coverage.

### Database

- All new tables require an Alembic migration.
- Foreign keys must use `CASCADE` delete with appropriate indexes.
- CHECK constraints for bounded values (confidence ≤ 0.85, scores 0–100).

## TypeScript Standards (Frontend — `apps/web/`)

### Type Safety

- **Strict mode** enabled. No `any` types — use `unknown` and narrow.
- Explicit return types on all exported functions.
- API response types must mirror backend Pydantic schemas
  (defined in `types/api/`).

### Naming & Style

- `camelCase` for variables and functions.
- `PascalCase` for types, interfaces, classes, and React components.
- `SCREAMING_SNAKE_CASE` for constants.
- `const` over `let`; immutability preferred.

### React Patterns

- Use **TanStack Query v5** for all data fetching (no raw `fetch` in components).
- Query keys centralized in `lib/query-keys.ts`.
- API client methods in `lib/api-client/<domain>.ts`.
- Hooks in `hooks/api/use-<domain>.ts` — auth-gated queries must check
  `isAuthenticated` via `enabled` option.
- `'use client'` directive required for client components.

### Linting & Build

- **ESLint** must pass with zero errors.
- **TypeScript** compilation (`tsc --noEmit`) must pass with zero errors.
- `next build` must complete successfully.

### Testing

- **Vitest** + `happy-dom` for unit tests.
- **Playwright** for E2E and visual regression tests.
- Coverage thresholds: 80% lines, 75% branches, 80% functions.

## Mobile Standards (Mobile — `apps/mobile/`)

### Patterns

- Expo Router v4 for navigation.
- **SecureStore** for token storage (never AsyncStorage for secrets).
- Icons from `@expo/vector-icons/Ionicons` via the centralized icon registry.
- Shared types imported from `@pathforge/shared`.

## Git & Commit Standards

### Conventional Commits

All commits must follow: `type(scope): description`

- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`
- **Scopes**: `api`, `web`, `mobile`, `shared`, `ci`, `infra`
- Flag commits that don't follow this convention.

### Branch Rules

- `main` — development integration branch
- `production` — deployed production code
- `dev/emre` — active development branch (PR source)
- Feature branches: `feat/<scope>-<description>` (e.g., `feat/web-pricing-redesign`)
- Never commit `.env` files, `node_modules`, or secrets.

## Architecture Rules

### Monorepo Boundaries

- `apps/web` must NOT import directly from `apps/api`.
- `apps/mobile` must NOT import directly from `apps/web`.
- Shared types belong in `packages/shared/src/types/`.
- API communication happens through typed HTTP clients, never direct imports.

### AI Engine Pattern (Backend)

Each career intelligence engine follows this pattern:

1. **Models** — SQLAlchemy models in `app/models/<engine>.py`
2. **Schemas** — Pydantic in `app/schemas/<engine>.py`
3. **Analyzer** — LLM methods in `app/ai/<engine>_analyzer.py`
4. **Service** — Orchestration in `app/services/<engine>_service.py`
5. **Routes** — FastAPI router in `app/api/v1/<engine>.py`

Flag any deviation from this pattern.

## Review Focus Areas

When reviewing PRs, prioritize in this order:

1. **Security** — secrets exposure, injection risks, missing sanitization
2. **Type safety** — missing types, `any` usage, unvalidated inputs
3. **Architecture** — monorepo boundary violations, pattern deviations
4. **Performance** — N+1 queries, missing indexes, unnecessary re-renders
5. **Testing** — missing tests for new endpoints/components
6. **Naming** — unclear names, abbreviations, inconsistent conventions
