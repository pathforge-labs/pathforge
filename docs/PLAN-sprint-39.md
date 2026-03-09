# Sprint 39 Plan — Auth Hardening & Email Service (Tier-1 Audit • Pass 3)

> Generated: 2026-03-09 · Audited: 2026-03-09 (Pass 3 — Final) · Velocity: 3.7× (split approved)
>
> **Decisions**: Sprint split ✅ · Option A pricing SSOT ✅ · Both OAuth providers ✅

---

## Tier-1 Audit Summary — 30 Findings

### 🔴 Critical (8)

| #   | Finding                                                                                                                                                                                                  | File(s)                                         | Evidence                                                                                                                                                 |
| :-- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F3  | `jwt_secret` default `"pathforge-dev-secret-change-in-production"` (L65) NOT in `_INSECURE_JWT_DEFAULTS` (L183-186). Frozenset only has 2 other values. **Default secret passes production validation.** | `config.py` L65, L183-186                       | `_INSECURE_JWT_DEFAULTS = frozenset({"change-me-in-production-use-a-real-secret", "change-me-refresh-secret-must-differ"})` — missing the actual default |
| F4  | `hashed_password` is `nullable=False` (L38) — blocks OAuth user creation                                                                                                                                 | `models/user.py` L38                            | `mapped_column(String(128), nullable=False)`                                                                                                             |
| F7  | `landing-data.ts` has duplicate `PricingTier` interface with different shape than `pricing.ts`                                                                                                           | `landing-data.ts` L113-125, `pricing.ts` L33-52 | 9 vs 11 fields, different names                                                                                                                          |
| F16 | `PricingCards` imports `PRICING_TIERS` from `@/data/landing-data` not `pricing.ts`                                                                                                                       | `pricing-cards.tsx` L6                          | `import { PRICING_TIERS } from "@/data/landing-data"`                                                                                                    |
| F23 | `UserService.authenticate()` calls `verify_password(password, user.hashed_password)` — crashes with `TypeError` when `hashed_password=None`                                                              | `user_service.py` L66                           | `passlib.verify()` expects string, gets `None`                                                                                                           |
| F24 | `UserService.create_user()` has mandatory `password: str` param — cannot create OAuth users                                                                                                              | `user_service.py` L30                           | Signature: `create_user(db, *, email, password, full_name)`                                                                                              |
| F28 | Register page auto-logins after registration — must redirect to "verify your email" page instead                                                                                                         | `register/page.tsx` L40-43                      | `await authApi.login(...)` immediately after register                                                                                                    |
| F30 | `jwt_secret` default (L65) is the actual value `"pathforge-dev-secret-change-in-production"` — identical to F3 but confirms the default matches what `_model_validator` should block                     | `config.py` L65 vs L183                         | Default = `"pathforge-dev-secret-change-in-production"`, not in frozenset                                                                                |

### ⚠️ Important (10)

| #   | Finding                                                                                                                                                 | File(s)                                  | Evidence                                          |
| :-- | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------------------------------------- | :------------------------------------------------ |
| F8  | Tier name "Starter" (landing-data) vs "Free" (pricing.ts)                                                                                               | `landing-data.ts` L129, `pricing.ts` L57 | Name mismatch                                     |
| F9  | Feature lists differ between landing-data and pricing.ts                                                                                                | Both files                               | Different descriptions per tier                   |
| F10 | Password `min_length=8` only — no complexity regex                                                                                                      | `schemas/user.py` L16                    | `Field(min_length=8, max_length=128)`             |
| F17 | `PricingCards` uses `tier.price`, `tier.period`, `tier.icon`, `tier.gradient` — not in `pricing.ts`                                                     | `pricing-cards.tsx` L97-106              | Adapter needs 8+ field mappings                   |
| F18 | Frontend `auth.ts` missing new methods                                                                                                                  | `lib/api-client/auth.ts`                 | Only has `register`, `login`, `refresh`, `logout` |
| F19 | `RegisterRequest` type missing `turnstile_token`                                                                                                        | `types/api/auth.ts` L12-16               | No CAPTCHA field                                  |
| F22 | Rate limit config missing for new auth endpoints                                                                                                        | `config.py`                              | No forgot/reset/verify rate limits                |
| F27 | Login page has NO "Forgot Password?" link                                                                                                               | `login/page.tsx` L35-86                  | No link to forgot-password                        |
| F29 | Register page client-side validation only checks `password.length < 8` — doesn't enforce complexity                                                     | `register/page.tsx` L29-32               | No uppercase/digit/special char check             |
| F26 | Pricing adapter needs mapping: `monthlyPrice→price`, `highlighted→popular`, `ctaText→cta`, add `icon`/`gradient`/`period`/`description`/`annualSavings` | Two files                                | Completely different interface shape              |

### 🟡 Redundant Tasks Removed (2)

| #   | Finding                                           | Evidence      |
| :-- | :------------------------------------------------ | :------------ |
| F1  | `auth_provider` already on User model (Sprint 34) | `user.py` L42 |
| F2  | `is_verified` already on User model               | `user.py` L41 |

### 🟢 Confirmed Good (10)

| #   | Finding                                                                                 |
| :-- | :-------------------------------------------------------------------------------------- |
| F5  | Resend config (`resend_api_key`, `digest_from_email`) exists in `config.py`             |
| F6  | Existing email uses raw httpx — new service uses `resend` SDK                           |
| F11 | `UserResponse` already has `is_verified` + `auth_provider`                              |
| F13 | `auth-provider.tsx` `AuthUser` type already correct                                     |
| F14 | SlowAPI `@limiter.limit()` pattern established on all auth routes                       |
| F15 | 25 Alembic migrations with consistent naming convention                                 |
| F20 | `RegisterCredentials` in `auth-provider.tsx` needs update — tracked                     |
| F21 | Existing tests `test_auth.py` + `test_auth_integration.py` — extend, not replace        |
| F25 | `SubscriptionTier = "free" \| "pro" \| "premium"` in `billing.ts`                       |
| F12 | No `verification_token` or `verification_sent_at` on User — expected, add via migration |

---

## Strategic Objectives

1. **Close 5 of 8 P0 blockers** (P0-1 password reset, P0-2 email verification, P0-3 email service, P0-4 JWT bypass, P0-7 pricing SSOT)
2. **Close 3 P1 blockers** (P1-3 CAPTCHA, P1-4 password policy, P1-6 CTA copy)
3. **Establish email infrastructure** — Resend SDK wrapper reusing existing config
4. **OAuth social login** — Google + Microsoft (P0-8)
5. **Pricing SSOT** — Option A: `PricingCards` consumes `pricing.ts` with marketing adapter

---

## Platform Health

| Domain       | Rating | Notes                                                                                          |
| :----------- | :----- | :--------------------------------------------------------------------------------------------- |
| Architecture | ✅     | 12 AI engines, 30 services, clean boundaries, 25 migrations                                    |
| Security     | 🔴     | JWT bypass F3/F30, no email verification, no password reset, no CAPTCHA, weak password         |
| Reliability  | ⚠️     | Rate limiting degrades gracefully, token blacklist Redis-backed                                |
| Product      | ⚠️     | Pricing SSOT broken (F7/F16/F17), register auto-logins (F28), no "Forgot Password?" link (F27) |
| Velocity     | ✅     | 1,345 tests, CI clean, 38-sprint history                                                       |

---

## Sprint 39A — Auth Foundation & Quick Fixes (17 tasks, 2–3 sessions)

### Phase A — Quick Fixes (1 session)

**A1. P0-4: JWT default bypass fix**

- File: `apps/api/app/core/config.py` L183
- Change: Add `"pathforge-dev-secret-change-in-production"` to `_INSECURE_JWT_DEFAULTS` frozenset
- Verify: `environment=production` + default `jwt_secret` → startup raises `ValueError`

**A2. P0-7/F7/F16/F17/F26: Pricing SSOT — Option A refactor**

- Files:
  - `apps/web/src/config/pricing.ts` — SSOT (no changes to base interface)
  - `apps/web/src/data/landing-data.ts` — DELETE `PricingTier` interface (L113-125) + DELETE `PRICING_TIERS` export (L127-196), ADD `LANDING_TIERS` that imports from `pricing.ts` and extends with marketing fields (`icon: LucideIcon`, `gradient: string`, `description: string`, `period: string`, `price: string`, `annualSavings: string`)
  - `apps/web/src/components/pricing-cards.tsx` L6 — update import to `LANDING_TIERS` from `@/data/landing-data`
- Design: Create `LandingTier` interface extending `PricingTier` from `pricing.ts`:
  ```typescript
  import {
    PRICING_TIERS,
    type PricingTier,
    formatPrice,
    getAnnualSavingsPercent,
  } from "@/config/pricing";
  interface LandingTier extends PricingTier {
    readonly icon: LucideIcon;
    readonly gradient: string;
    readonly description: string;
    readonly price: string; // derived from formatPrice(monthlyPrice)
    readonly period: string; // derived "/mo" or "forever"
    readonly annualPrice: string; // derived formatPrice(annualPrice)
    readonly annualSavings: string; // derived from getAnnualSavingsPercent()
    readonly popular: boolean; // alias for highlighted
    readonly cta: string; // alias for ctaText
  }
  ```
- Verify: `npx tsc --noEmit`, single `PricingTier` source, tier names (Free/Pro/Premium), correct CTAs, no "Join Waitlist"

**A3. P1-4/F10: Password complexity validator**

- File: `apps/api/app/schemas/user.py` L14-18
- Change: Add `@field_validator("password")` with 3 regex checks (uppercase, digit, special char)
- Error message: `"Password must contain at least one uppercase letter, one digit, and one special character"`
- Verify: `"password1"` → 422, `"P@ssw0rd!"` → 200

**A4. F29: Frontend password complexity sync**

- File: `apps/web/src/app/(auth)/register/page.tsx` L29-32
- Change: Replace `password.length < 8` with regex validation matching backend rules
- Verify: client-side shows error before API call for weak passwords

**A5. F27: "Forgot Password?" link on login page**

- File: `apps/web/src/app/(auth)/login/page.tsx`
- Change: Add `<Link href="/forgot-password">` below password field
- Verify: "Forgot Password?" link visible and clickable on login page

### Phase B — Email Service (1–2 sessions)

**B1. Install `resend` Python SDK**

- File: `apps/api/pyproject.toml`
- Command: `uv add resend`
- Verify: `uv pip install -e .` succeeds

**B2. Create email service**

- File: `apps/api/app/services/email_service.py` [NEW]
- Methods: `send_verification_email(to, token, name)`, `send_password_reset_email(to, token, name)`, `send_welcome_email(to, name)`
- Pattern: graceful degradation when `resend_api_key` empty (log + return, never crash), reuse `settings.digest_from_email`
- Verify: imports clean, dev mode logs "Email delivery disabled"

**B3. HTML email templates**

- Directory: `apps/api/app/templates/email/` [NEW]
- Files: `verification.html`, `password_reset.html`, `welcome.html`
- Verify: templates render with sample data

**B4. Config additions**

- File: `apps/api/app/core/config.py`
- New fields: `password_reset_token_expire_minutes: int = 30`, `email_verification_token_expire_hours: int = 24`, `rate_limit_forgot_password: str = "3/minute"`, `rate_limit_reset_password: str = "5/minute"`, `rate_limit_verify_email: str = "5/minute"`, `rate_limit_resend_verification: str = "3/minute"`, `turnstile_secret_key: str = ""`
- Verify: settings load from env

**B5. 🔧 MANUAL: Resend API key**

- Action: Generate at resend.com → set `RESEND_API_KEY` in Railway
- Verify: test email send succeeds

### Phase C — Password Reset (1 session)

**C1. Alembic migration — Sprint 39 auth hardening**

- File: `apps/api/alembic/versions/{hash}_sprint_39_auth_hardening.py` [NEW]
- Changes:
  - ADD `verification_token: String(128), nullable=True`
  - ADD `verification_sent_at: DateTime(timezone=True), nullable=True`
  - ALTER `hashed_password`: `nullable=False` → `nullable=True` (F4)
- Down: drop 2 columns, restore `hashed_password` NOT NULL with `server_default=""`
- Verify: `alembic upgrade head` + `alembic downgrade -1` succeed

**C2. Forgot password endpoint — `POST /auth/forgot-password`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Schema: `ForgotPasswordRequest(email: EmailStr)` in `schemas/user.py`
- Security: ALWAYS return `{"message": "If an account exists, a reset email was sent"}` (prevent email enumeration)
- Rate limit: `@limiter.limit(settings.rate_limit_forgot_password)`
- Logic: generate `secrets.token_urlsafe(32)`, store hash on user model (not raw token — store `hashlib.sha256(token).hexdigest()`), send email with raw token link
- Verify: 200 for valid + invalid emails, rate limited 3/min

**C3. Reset password endpoint — `POST /auth/reset-password`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Schema: `ResetPasswordRequest(token: str, new_password: str)` with password complexity validator
- Logic: hash incoming token, compare to stored hash, check expiry, hash new password, clear token
- Rate limit: `@limiter.limit(settings.rate_limit_reset_password)`
- Verify: valid token → password updated, expired → 400, used → 400

**C4. Frontend — forgot-password page**

- File: `apps/web/src/app/(auth)/forgot-password/page.tsx` [NEW]
- Pattern: email input → submit → "Check your email" success state
- Verify: form renders, submits, shows success

**C5. Frontend — reset-password page**

- File: `apps/web/src/app/(auth)/reset-password/page.tsx` [NEW]
- Pattern: token from URL `?token=...`, new password + confirm, submit
- Verify: form renders, validates passwords match + complexity, submits

**C6. Frontend auth API client + types for password reset**

- File: `apps/web/src/lib/api-client/auth.ts` [MODIFY]
- New: `forgotPassword(email)`, `resetPassword(token, newPassword)`
- File: `apps/web/src/types/api/auth.ts` [MODIFY]
- New: `ForgotPasswordRequest`, `ResetPasswordRequest`
- Verify: `npx tsc --noEmit`

**C7. Tests — password reset**

- File: `apps/api/tests/test_auth_password_reset.py` [NEW]
- Cases: happy path, expired token, invalid token, used token, rate limit, email enumeration prevention, password complexity on reset
- Verify: `pytest tests/test_auth_password_reset.py -v`

---

## Sprint 39B — Email Verification, CAPTCHA & OAuth (18 tasks, 3–4 sessions)

### Phase D — Email Verification + CAPTCHA (1–2 sessions)

**D1. Verify email endpoint — `POST /auth/verify-email`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Schema: `VerifyEmailRequest(token: str)` in `schemas/user.py`
- Logic: hash token, compare to stored hash, set `is_verified=True`, clear token
- Verify: valid → verified, invalid → 400

**D2. Resend verification — `POST /auth/resend-verification`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Rate limit: `@limiter.limit(settings.rate_limit_resend_verification)`
- Logic: generate new token, send email, update `verification_sent_at`
- Verify: new email sent, old token invalid, rate limited

**D3. Registration → auto-send verification + F28 fix**

- File: `apps/api/app/api/v1/auth.py` — modify `register()` (L42-58)
- Change: after `UserService.create_user()`, generate token, send verification email
- File: `apps/web/src/app/(auth)/register/page.tsx` — F28 fix
- Change: remove auto-login (L40-43), redirect to "/verify-email" confirmation page
- Verify: registration creates user + sends email, frontend shows "Check your email"

**D4. Frontend — verify-email landing page**

- File: `apps/web/src/app/(auth)/verify-email/page.tsx` [NEW]
- Pattern: shows "Check your email" message with "Resend" button
- Verify: page renders, resend button works

**D5. Turnstile CAPTCHA — backend**

- File: `apps/api/app/api/v1/auth.py` [MODIFY], `schemas/user.py` [MODIFY]
- Schema: add `turnstile_token: str | None = None` to `UserRegisterRequest`
- Config: `turnstile_secret_key` already added in B4
- Logic: if `turnstile_secret_key` configured, POST to Cloudflare API, reject invalid tokens
- Graceful: if `turnstile_secret_key` empty (dev), skip CAPTCHA validation
- Verify: prod mode without token → 422; dev mode without token → accepted

**D6. Frontend CAPTCHA + types**

- File: `apps/web/src/types/api/auth.ts` — add `turnstile_token` to `RegisterRequest`
- File: `apps/web/src/providers/auth-provider.tsx` — add `turnstileToken` to `RegisterCredentials`
- File: `apps/web/src/app/(auth)/register/page.tsx` — add Turnstile widget (`@cloudflare/turnstile-widgets` or script tag)
- Verify: `npx tsc --noEmit`, registration shows CAPTCHA widget

**D7. Frontend auth API client — verification methods**

- File: `apps/web/src/lib/api-client/auth.ts` — add `verifyEmail(token)`, `resendVerification(email)`
- File: `apps/web/src/types/api/auth.ts` — add `VerifyEmailRequest`
- Verify: `npx tsc --noEmit`

**D8. Tests — email verification + CAPTCHA**

- File: `apps/api/tests/test_auth_verification.py` [NEW]
- Cases: verify happy path, expired token, registration sends email, CAPTCHA validation, CAPTCHA skip in dev
- Verify: `pytest tests/test_auth_verification.py -v`

### Phase E — OAuth / Social Login (2–3 sessions)

**E1. 🔧 MANUAL: Google OAuth client**

- Google Cloud Console → Credentials → OAuth 2.0 Client ID
- Origins: `https://pathforge.eu`, `http://localhost:3000`
- Set: `GOOGLE_OAUTH_CLIENT_ID` + `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

**E2. 🔧 MANUAL: Microsoft OAuth app**

- Azure AD → App registrations
- Redirect: `https://pathforge.eu/auth/callback/microsoft`
- Set: `MICROSOFT_OAUTH_CLIENT_ID` + `MICROSOFT_OAUTH_CLIENT_SECRET`

**E3. OAuth config + dependencies**

- File: `apps/api/app/core/config.py` — add `google_oauth_client_id`, `microsoft_oauth_client_id`, `microsoft_oauth_client_secret` (empty defaults)
- File: `apps/api/pyproject.toml` — add `google-auth`, `msal`
- Verify: settings load

**E4. F24: UserService.create_user() — OAuth overload**

- File: `apps/api/app/services/user_service.py` [MODIFY]
- Change: `create_user(db, *, email, password=None, full_name, auth_provider="email", is_verified=False)`
- Logic: if `password` provided, hash it; if None, set `hashed_password=None` (OAuth user)
- Add method: `find_or_create_oauth_user(db, *, email, full_name, auth_provider)` — creates with `is_verified=True`, `hashed_password=None`
- Verify: OAuth user created with null password

**E5. F23: UserService.authenticate() — guard NULL password**

- File: `apps/api/app/services/user_service.py` [MODIFY]
- Change: before `verify_password()`, check `if user.hashed_password is None: raise ValueError("Use social login for this account")`
- Verify: OAuth-only user gets 401 with social login message, email user still works

**E6. Google OAuth endpoint — `POST /auth/oauth/google`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Schema: `OAuthGoogleRequest(id_token: str)`
- Logic: `google.oauth2.id_token.verify_oauth2_token()` → extract email/name → `find_or_create_oauth_user()`
- Verify: valid Google token → PathForge JWT

**E7. Microsoft OAuth endpoint — `POST /auth/oauth/microsoft`**

- File: `apps/api/app/api/v1/auth.py` [MODIFY]
- Schema: `OAuthMicrosoftRequest(access_token: str)`
- Logic: call Microsoft Graph `/me` → extract email/name → `find_or_create_oauth_user()`
- Verify: valid Microsoft token → PathForge JWT

**E8. Frontend — OAuth buttons + SDKs**

- Files:
  - `apps/web/src/app/(auth)/login/page.tsx` — add "Continue with Google/Microsoft" buttons
  - `apps/web/src/app/(auth)/register/page.tsx` — add same buttons
  - `apps/web/src/lib/auth/google.ts` [NEW] — Google Identity Services SDK
  - `apps/web/src/lib/auth/microsoft.ts` [NEW] — `@azure/msal-browser` popup flow
  - `apps/web/src/lib/api-client/auth.ts` — add `oauthGoogle(idToken)`, `oauthMicrosoft(accessToken)`
  - `apps/web/src/types/api/auth.ts` — add `OAuthGoogleRequest`, `OAuthMicrosoftRequest`
  - `package.json` — add `@azure/msal-browser`
- Verify: `npx tsc --noEmit`, buttons visible, popup flows work

**E9. Tests — OAuth flows**

- File: `apps/api/tests/test_auth_oauth.py` [NEW]
- Cases: Google happy path (mock token verify), Microsoft happy path, account linking (same email), OAuth-only password-login rejection (F23), invalid tokens, missing config graceful degradation
- Verify: `pytest tests/test_auth_oauth.py -v`

**E10. Account linking strategy**

- File: `apps/api/app/services/user_service.py` — logic in `find_or_create_oauth_user()`
- Strategy: if email exists with different provider → update `auth_provider` to comma-separated (e.g., `"email,google"`)
- Guard: login endpoint already guarded by F23 fix (E5)
- Verify: existing email user + Google OAuth → linked, `auth_provider="email,google"`

---

## Dependency Chain

```
Phase A (Quick Fixes) → no blockers ✅
Phase B (Email Service) → no blockers ✅
    └── 🔧 MANUAL: Resend API key (prod only)
Phase C (Password Reset) → Phase B (email service)
    └── Includes Alembic migration (verification cols + hashed_password nullable)
Phase D (Email Verification + CAPTCHA) → Phase B + Phase C
Phase E (OAuth) → ⚠️ BLOCKED BY: 🔧 MANUAL OAuth app setup + Phase C migration
    └── E4/E5 depend on Phase C migration (hashed_password nullable)
```

---

## Risk Matrix

| Risk                                            | Sev   | Mitigation                            |
| :---------------------------------------------- | :---- | :------------------------------------ |
| JWT bypass in production (F3/F30)               | 🔴 P0 | Phase A task 1 — 1-line fix           |
| `hashed_password NOT NULL` blocks OAuth (F4)    | 🔴 P0 | Migration in Phase C                  |
| `authenticate()` crashes on OAuth users (F23)   | 🔴 P0 | Guard in Phase E (E5)                 |
| `create_user()` mandatory password (F24)        | 🔴 P0 | Overload in Phase E (E4)              |
| Register auto-login bypasses verification (F28) | 🔴 P0 | Fix in Phase D (D3)                   |
| Pricing dual-interface (F7/F16/F17)             | ⚠️ P1 | Adapter pattern in Phase A (A2)       |
| Token stored in plaintext                       | ⚠️ P1 | Store `sha256(token)`, compare hashed |
| Sprint 39B velocity 2.2×                        | ⚠️ P2 | Split into 39B/39C if needed          |

---

## Verification Plan

### Automated Tests

```powershell
# Backend — all tests
cd apps/api
.venv\Scripts\python.exe -m pytest tests/ -x --timeout=30

# New test files
.venv\Scripts\python.exe -m pytest tests/test_auth_password_reset.py -v
.venv\Scripts\python.exe -m pytest tests/test_auth_verification.py -v
.venv\Scripts\python.exe -m pytest tests/test_auth_oauth.py -v

# Existing tests (MUST still pass)
.venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_auth_integration.py -v

# Linting + Type checks
cd apps/api; .venv\Scripts\python.exe -m ruff check app/ --quiet
cd apps/web; pnpm lint
cd apps/web; npx tsc --noEmit

# Build
cd apps/web; pnpm build
```

### Manual Verification

1. **JWT guard**: Set `environment=production` + leave default `jwt_secret` → startup MUST crash
2. **Pricing**: Landing page pricing section → correct tier names (Free/Pro/Premium), CTAs ("Get Started"/"Upgrade to Pro"/"Upgrade to Premium"), no "Join Waitlist"
3. **Password reset**: Login → "Forgot Password?" → email → link → new password → login
4. **Registration**: Register → "Check your email" page (NO auto-login) → verify email → login
5. **OAuth**: "Continue with Google" → popup → dashboard with correct `auth_provider`
6. **OAuth password guard**: OAuth-only user → login page → email/password → "Use social login" error

---

## Task Count Summary

| Phase                            | Tasks  | Sprint |
| :------------------------------- | :----- | :----- |
| A — Quick Fixes                  | 5      | 39A    |
| B — Email Service                | 5      | 39A    |
| C — Password Reset               | 7      | 39A    |
| D — Email Verification + CAPTCHA | 8      | 39B    |
| E — OAuth                        | 10     | 39B    |
| **Total**                        | **35** |        |

---

## User Review Required

> [!WARNING]
> **F3/F30 — JWT Secret Bypass**: The default `jwt_secret` value (`"pathforge-dev-secret-change-in-production"`) on config.py line 65 is **NOT** in the `_INSECURE_JWT_DEFAULTS` frozenset on line 183. This means the production validator DOES NOT block this default. This is a live security vulnerability — any production deployment using default config has a guessable JWT secret. **Fix is a single-line change (Phase A, task 1).**

> [!WARNING]
> **F23/F24 — OAuth will crash `authenticate()`**: `verify_password(password, None)` will raise `TypeError` in passlib. The `create_user()` method also requires `password` as a mandatory parameter. Both need modification before OAuth can work.

> [!IMPORTANT]
> **F28 — Register auto-login**: Current register page (line 40-43) does `await authApi.login(...)` immediately after registration, bypassing email verification entirely. This must be changed to redirect to a "verify your email" confirmation page.

> [!IMPORTANT]
> **C2 — Password reset token security**: Reset tokens MUST be stored as SHA-256 hashes (not plaintext) on the User model. The raw token is sent via email; the hashed version is stored. This prevents database leaks from being exploitable.

> [!IMPORTANT]
> **3 manual blockers** (same as previous pass): Resend API key, Google OAuth client, Microsoft OAuth app.
