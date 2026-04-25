# ADR-0006 — Auth via httpOnly cookies (Track 1, Sprint 55)

> **Status**: Accepted · **Date**: 2026-04-25
> **Authors**: Claude (Senior Staff)
> **Related**: §6 R8 of `docs/MASTER_PRODUCTION_READINESS.md`; `docs/architecture/sprint-55-58-code-side-readiness.md` Track 1.

---

## Context

PathForge stored JWT access + refresh tokens in `localStorage` since Sprint 31. Risk documented as accepted in `MASTER_PRODUCTION_READINESS.md` §6 R8: any cross-site script execution (XSS) on `pathforge.eu` can read both tokens via `localStorage.getItem(...)` and exfiltrate them.

Defence has been Content Security Policy (CSP) + Subresource Integrity (SRI), which closes most XSS classes — but the *primary* OWASP-recommended defence (taking JS out of the auth-token path) was missing.

Industry baseline at our user count (4-figure MAU pre-launch, growing into five figures post-launch) is `httpOnly` cookies for auth tokens. LinkedIn, Indeed, Glassdoor, GitHub, and Vercel itself all use cookie auth.

The Sprint 55 plan in `sprint-55-58-code-side-readiness.md` Track 1 was approved to close this gap.

## Decision

Move PathForge web auth to **first-party `httpOnly` + `Secure` + `SameSite=Strict` cookies** with **double-submit CSRF protection**:

1. `pathforge_access` (httpOnly) — JWT access token, ~60 min lifetime.
2. `pathforge_refresh` (httpOnly) — JWT refresh token, ~30 day lifetime.
3. `pathforge_csrf` (NOT httpOnly) — random 256-bit token; client JS reads it and echoes the value in the `X-CSRF-Token` header on mutating requests; server compares cookie vs header in constant time.

The legacy `Authorization: Bearer` header path is **not removed**. For 30 days the server reads either source. After `AUTH_LEGACY_HEADER_DEPRECATED_AFTER` (a configurable date) bearer-header requests still work but emit a Sentry warning so we can observe the long-tail of un-migrated clients.

## Considered alternatives

### A. Keep localStorage; harden CSP further
Rejected. CSP bypasses are a regular finding in security research; defence in depth requires also closing the JS-read-the-token path. The cookie path also reduces JS work on every authenticated request (no localStorage read).

### B. httpOnly cookie + `SameSite=Strict`, no CSRF
Rejected. Safari's Intelligent Tracking Prevention has historically downgraded `SameSite=Strict` silently; certain OAuth redirect flows also weaken it. We want belt-and-suspenders given that auth tokens are the highest-value cookie on the platform.

### C. Server-side session store (no JWT at all)
Rejected. Redis-backed session lookup adds latency to every authenticated call. We already use Redis for the JWT blacklist (ADR-0002), and we don't want to widen the critical path more than necessary. JWT-in-cookie keeps the verify-locally property of the existing design.

### D. Cookie auth only, drop bearer immediately
Rejected. A breaking-change PR for the auth path would destabilise the mobile and web clients in flight. The 30-day overlap window matches our mobile release cadence and gives us time to observe the rollout via the `auth.path` Sentry tag.

## Consequences

### Positive
- **XSS exfiltration class closed** for auth tokens. Even a fully successful XSS now cannot directly read the access or refresh JWT.
- **CSRF surface closed** on cookie auth via standard double-submit.
- **Mobile unchanged** (`expo-secure-store` is already not localStorage).
- **Logout is now stricter and safer**: previously a client that forgot to pass the refresh token in the body left the long-lived token live; the server now revokes the cookie refresh too. This is a strict security improvement that we explicitly tested.
- **OAuth path equally protected** — `oauth_login` also sets cookies.
- **CORS already correct**: `allow_credentials=True` plus a non-`*` origin list (validated by config-guards CI job) is the only safe configuration for cross-origin cookie auth, and we already had it.

### Negative
- **Web SDK contract changed** (`apps/web/src/lib/http.ts`): every fetch now sends `credentials: "include"` and attaches an `X-CSRF-Token` header on mutating requests. Invisible to feature code that uses `fetchWithAuth` / `get` / `post` etc. — but anyone using raw `fetch` against the API is broken, which is forbidden by convention.
- **E2E fixtures must seed cookies**, not localStorage. Playwright visual-regression auth fixture is the only known consumer; ships in a follow-up PR with a `setAuthCookies(page, user)` helper.
- **Test contract changed**: existing logout tests asserting "only access revoked when no refresh in body" had to be updated to "access + cookie-refresh both revoked". The change is a strict improvement.
- **30-day legacy window** keeps the bearer read path live; security posture is unchanged for clients on the legacy path. After `AUTH_LEGACY_HEADER_DEPRECATED_AFTER` we expect bearer usage to drop to under 5%; the residual is observable via Sentry warning.

### Operational notes
- `Secure` is auto-derived: `True` in production, `False` only when `ENVIRONMENT != "production"` so cookies still flow over plaintext localhost dev.
- `SameSite=Strict` is set in all environments. This means the auth cookies do not flow on cross-site top-level navigation — a desired property for a career platform (no CSRF on link click) but worth noting for any future "shareable preview link" feature.
- The CSRF cookie is intentionally NOT httpOnly so the SPA can read it. This is correct per OWASP — the cookie itself is the secret; exposure to JS is the design.

## Verification (post-merge)

| Probe | Expected |
|:---|:---|
| `curl -i POST /api/v1/auth/login` (with valid creds) | 3 `Set-Cookie` headers on response, body still has `access_token` and `refresh_token` |
| Browser dev tools after login | `pathforge_access` and `pathforge_refresh` show as `httpOnly`, `Secure` (in production), `SameSite=Strict`; `pathforge_csrf` shows as `Secure` only (not httpOnly) |
| `GET /api/v1/users/me` with cookies but no Authorization header | 200 |
| `POST /api/v1/auth/logout` with cookie but no `X-CSRF-Token` | 403, `csrf.violation=missing_header` Sentry breadcrumb |
| `POST /api/v1/auth/logout` with cookie + valid `X-CSRF-Token` | 204, both access JTI and refresh JTI in blacklist |
| Sentry tag `auth.path` distribution after 7 days | `cookie` >= 95% |

## Rollback

- Revert the merge commit. The cookie path code is purely additive on the server (the bearer path was never removed) and adds three new files (`csrf.py`, `test_auth_cookie_path.py`, this ADR). Reversion yields the pre-T1 state with no schema or data migration.
- The web client change is a single commit on `apps/web/src/lib/http.ts` — revertable independently.
- Mobile is unchanged.

## Telemetry

The Sentry `auth.path` breadcrumb tag (`cookie | bearer | none`) is emitted by `get_current_user`. The 7-day dashboard probe in §11 of `docs/architecture/sprint-55-58-code-side-readiness.md` validates that >= 95% of authenticated requests hit the cookie path within the rollout window.

## References

- OWASP Cheatsheet — JWT for Java § "Token sidejacking"
- OWASP CSRF Prevention Cheat Sheet § "Synchronizer Token / Double-Submit"
- ADR-0001 — Database SSL secure-by-default
- ADR-0002 — Redis SSL secure-by-default
- `docs/architecture/sprint-55-58-code-side-readiness.md` Track 1
- `docs/MASTER_PRODUCTION_READINESS.md` §6 R8
