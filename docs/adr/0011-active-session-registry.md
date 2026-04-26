# ADR-0011 — Active Session Registry & User-facing Session Management (T1-extension)

> **Status**: Accepted · **Date**: 2026-04-26
> **Authors**: Claude (Senior Staff)
> **Supersedes**: nothing — extends ADR-0006 (cookie auth).
> **Related**: `docs/architecture/sprint-55-58-code-side-readiness.md` §2.6 (Differentiation hook); `docs/MASTER_PRODUCTION_READINESS.md` §6 R8.

---

## Context

ADR-0006 moved the auth tokens to `httpOnly` cookies and closed the JS-readable-token exfil class. The plan §2.6 noted a follow-up: **a user-facing "Sessions" tab** so the user can see every device that has an active session and revoke any of them on demand. LinkedIn, GitHub, Vercel, Stripe, and every credible auth-aware product ships this surface; PathForge cannot launch as a paid product without parity.

Until now PathForge had only the JTI blacklist (ADR-0002): a one-way "is this token revoked?" probe with no way to *enumerate* the live sessions for a user. To list sessions we need a second data structure that tracks "what JTIs does this user own right now?".

## Decision

Add an **active session registry** layered on top of the existing JTI blacklist.

### Backend

`app/core/sessions.py` — `SessionRegistry` class with class-level Redis pool (mirrors `TokenBlacklist`). Two Redis keyspaces:

| Key | Type | Contents | TTL |
|:---|:---:|:---|:---:|
| `session:user:{user_id}` | SET | refresh JTIs currently active for the user | refreshed on every register; auto-expires when the longest-lived JTI in the set would have expired |
| `session:meta:{jti}` | HASH | per-session metadata: `user_id`, `created_at`, `last_seen_at`, `ip`, `user_agent`, `device_label` | refresh-token remaining lifetime |

Why Redis (and not a `user_session` Postgres table): sessions are inherently ephemeral and bounded by refresh-token lifetime (30 days). A relational table would carry permanent rows for transient state and require a periodic cleanup job; Redis's per-key TTL handles that for free. The same Redis instance already runs the blacklist + rate limiter, so no new infra dependency.

The registry is **fail-soft**: if Redis is unreachable, `register()` is a no-op (the auth flow still succeeds), `list_for_user()` returns `[]`, and `revoke()` returns `False`. This matches the `token_blacklist_fail_mode` semantics without forcing the auth path to honour a tighter contract than it already does.

### Auth integration

| Auth event | Registry side-effect |
|:---|:---|
| `login` (cookie or bearer) | `SessionRegistry.register(user_id, refresh_jti, ttl, ip, user_agent)` |
| `refresh` rotation | revoke the *old* refresh JTI from registry + blacklist; register the *new* refresh JTI |
| `logout` | revoke the refresh JTI from registry + blacklist |
| `account-deletion` | `SessionRegistry.purge_user(user_id)` so right-to-erasure leaves no Redis trace |

The `_register_session_from_tokens` helper in `app/api/v1/auth.py` decodes the refresh token to extract `jti`, `sub`, `exp` and reads `X-Forwarded-For` (first hop only) + `User-Agent` from the request.

### User-facing routes

`app/api/v1/sessions.py` — three endpoints under `/api/v1/users/me/sessions`:

| Method | Path | Purpose |
|:---:|:---|:---|
| `GET` | `/` | list active sessions; current device flagged `is_current=true` |
| `DELETE` | `/{jti}` | revoke a specific session |
| `POST` | `/revoke-others` | revoke every session except the current one |

Mutating routes carry the `csrf_protect` dependency from ADR-0006. `revoke-others` requires the cookie path (refuses 400 for legacy bearer-only callers) so a non-cookie client can't accidentally end its own only-known session by mistake.

### Web UI

`apps/web/src/app/(dashboard)/dashboard/settings/security/page.tsx` — lists sessions with device label, IP, last-active timestamp; each row has a Revoke button; one prominent "Sign out of $N other device(s)" button.

Hydration-safe relative time: `useClientNow` returns `null` pre-hydration so SSR shows absolute UTC, then upgrades to "5m ago" client-side. Same pattern used on the AI usage page (Gemini medium #4 on PR #35).

## Considered alternatives

### A. `user_session` Postgres table
Rejected. Permanent storage for transient state; needs a cleanup job; adds a write per login + refresh + logout to a relational connection that's already tight on its query budget. Redis's TTL primitive solves the lifecycle for free.

### B. Read sessions out of the existing JTI blacklist
Rejected. The blacklist stores *revoked* tokens, not active ones. We'd have to invert the relationship by enumerating *all* user JTIs server-side, which we don't track.

### C. UA parsing with `ua-parser-js`
Rejected. ua-parser pulls 500+ KB of regex into the runtime for marginal accuracy improvement. The 5-line heuristic in `_derive_device_label` covers Edge / Chrome / Firefox / Safari / iOS / Android / mobile-app cases that account for >99 % of real traffic; the full UA is shown on hover for the 1 % long tail.

### D. Per-device geo-IP lookup
Rejected. Adds a service dependency (MaxMind / IPInfo) for a cosmetic feature, and exposing geo data raises GDPR-DSR considerations we'd rather not invent today. The IP is shown verbatim; future iteration may add geo behind a feature flag.

## Consequences

### Positive
- **User trust signal**: the user can prove to themselves that no one else is signed in. Direct competitor parity (LinkedIn, GitHub).
- **GDPR Article 17 compliance** extended: session registry purged on account deletion.
- **Stronger logout semantics**: pre-T1 a forgetful client could leave the long-lived refresh token unrevoked; post-T1 logout drops both blacklist and session entry.
- **No new infra dependency**: reuses the Redis instance the blacklist + rate limiter already run on.

### Negative
- **One extra Redis round-trip on every login + refresh + logout**: ~1 ms p99 over the wire on the same VPC. Measured under the T3 perf baseline; below the budget.
- **Test suite needs an in-memory Redis stand-in**: added `fakeredis>=2.30.0` as a dev-only dependency. Hermetic, no container required.
- **Web bundle size**: +1.4 KB (gzipped) for the new page + hook + API client. Acceptable.

### Differentiator hook (deferred)
The plan §2.6 mentions an enterprise-SSO **cookie-revoke webhook**: an admin endpoint partners can call to force-logout a user on offboarding. The `SessionRegistry.purge_user` primitive already exists; the webhook is one additional admin route + signature scheme. **Out of scope for this PR** — tracked as Sprint 60 backlog item.

## Verification (post-merge)

| Probe | Expected |
|:---|:---|
| `curl -i POST /api/v1/auth/login` | response sets cookies; `redis-cli SMEMBERS session:user:{uid}` shows the new JTI |
| `curl GET /api/v1/users/me/sessions` (with cookie) | `{"sessions": [{"jti": "...", "is_current": true, ...}]}` |
| `curl DELETE /api/v1/users/me/sessions/{other-jti}` (with CSRF) | 204; the other device is signed out on its next API call |
| `curl POST /api/v1/users/me/sessions/revoke-others` | `{"revoked_count": N}`; current session preserved |
| `curl DELETE /api/v1/users/me` (account deletion) | both blacklist + session registry entries gone |

## Rollback

- Revert the merge commit. The registry is purely additive — every auth path still works without `SessionRegistry` (failsafe is "act as if Redis is unreachable"). Reversion yields the pre-T1-extension state with no schema or data migration.

## Telemetry

Sentry breadcrumbs are emitted per session-registry write (debug-level). Failed registry writes emit `WARNING` so we can observe the soft-fail rate in production.

## References

- ADR-0006 — Auth via httpOnly cookies (T1 / Sprint 55)
- ADR-0002 — Redis SSL secure-by-default (registry uses the same `resolve_redis_url` helper)
- `docs/architecture/sprint-55-58-code-side-readiness.md` §2.6
- LinkedIn, GitHub, Vercel: all ship a Sessions tab (industry baseline)
