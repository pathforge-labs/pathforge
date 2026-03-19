# PathForge — Production Deployment Operator Checklist

Pre-launch checklist for deploying PathForge to production. Every item
must be verified before go-live.

---

## 1. Environment Variables

### Railway (API)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (Supabase) |
| `DATABASE_SSL` | Yes | Set `true` for production |
| `REDIS_URL` | Yes | Token blacklist, rate limiting |
| `JWT_SECRET` | Yes | ≥ 32 bytes, HMAC-SHA256 |
| `JWT_REFRESH_SECRET` | Yes | ≥ 32 bytes, separate from JWT_SECRET |
| `SENTRY_DSN` | Yes | Backend error tracking (P0-2) |
| `STRIPE_SECRET_KEY` | Yes | Stripe billing (P0-3) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Webhook signature verification |
| `ANTHROPIC_API_KEY` | Yes | LLM provider for career engines (P0-4) |
| `VOYAGE_API_KEY` | Yes | Embedding model for vector search (P0-4) |
| `TURNSTILE_SECRET_KEY` | Yes | Cloudflare Turnstile CAPTCHA |
| `SENDGRID_API_KEY` | Yes | Transactional email (verification, reset) |
| `GOOGLE_OAUTH_CLIENT_ID` | Conditional | Required if Google SSO enabled |
| `MICROSOFT_OAUTH_CLIENT_ID` | Conditional | Required if Microsoft SSO enabled |

### Vercel (Web)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Points to Railway API URL |
| `NEXT_PUBLIC_SENTRY_DSN` | Yes | Frontend error tracking (P0-2) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Yes | Stripe client key |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | Yes | Cloudflare Turnstile widget |
| `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` | Conditional | Google SSO |
| `NEXT_PUBLIC_MICROSOFT_OAUTH_CLIENT_ID` | Conditional | Microsoft SSO |

---

## 2. Database

- [ ] Run Alembic migrations: `alembic upgrade head`
- [ ] Verify SSL connection (`DATABASE_SSL=true`)
- [ ] Confirm connection pool settings (min=2, max=10 for Railway)
- [ ] Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector`
- [ ] Verify row-level security policies on Supabase dashboard

---

## 3. Redis

- [ ] Confirm `REDIS_URL` connects successfully
- [ ] Token blacklist fail mode set to `closed` (production default)
- [ ] Rate limiter storage backend configured
- [ ] Verify `PING` returns `PONG`

---

## 4. Security

- [ ] JWT secrets are unique, ≥ 32 bytes, not shared between environments
- [ ] JWT_REFRESH_SECRET differs from JWT_SECRET
- [ ] CORS origins restricted to production domains only
- [ ] Rate limiting enabled on all auth endpoints
- [ ] Turnstile CAPTCHA active on registration
- [ ] HTTPS enforced (no plain HTTP)
- [ ] No debug mode (`DEBUG=false`)
- [ ] No development secrets in production env

---

## 5. Monitoring & Observability

- [ ] **Sentry** (P0-2): Backend DSN configured, test error sent
- [ ] **Sentry** (P0-2): Frontend DSN configured, test error sent
- [ ] **UptimeRobot** (P1-5): Monitor `/health/ready` endpoint (1-minute interval)
- [ ] **Logging**: Structured JSON logs shipping to aggregator
- [ ] **Alerts**: Sentry alert rules configured for P0 errors

---

## 6. Stripe Billing

- [ ] `STRIPE_SECRET_KEY` is live-mode key (not test)
- [ ] `STRIPE_WEBHOOK_SECRET` matches webhook endpoint in Stripe dashboard
- [ ] Webhook endpoint registered: `POST /api/v1/billing/webhook`
- [ ] Products and prices created in Stripe dashboard
- [ ] Test: checkout flow creates subscription
- [ ] Test: webhook handles `invoice.paid` and `customer.subscription.deleted`

---

## 7. Email

- [ ] SendGrid API key configured with proper sender identity
- [ ] SPF and DKIM DNS records verified
- [ ] Verification email template renders correctly
- [ ] Password reset email template renders correctly
- [ ] Welcome email template renders correctly

---

## 8. LLM / AI Engines

- [ ] `ANTHROPIC_API_KEY` valid and has sufficient credits
- [ ] `VOYAGE_API_KEY` valid for embedding generation
- [ ] Rate limits on AI endpoints configured
- [ ] Fallback behavior tested (API down → graceful error)

---

## 9. Health Check Verification

```bash
# API readiness (includes DB + Redis + rate limiter)
curl -s https://api.pathforge.com/health/ready | jq .

# Expected: {"status": "healthy", "checks": {...}}
```

---

## 10. Post-Deploy Smoke Tests

- [ ] Register new user → receives verification email
- [ ] Verify email → user marked as verified
- [ ] Login → access + refresh tokens returned
- [ ] Refresh token → new token pair returned, old refresh revoked
- [ ] Logout → access token blacklisted
- [ ] Forgot password → reset email sent
- [ ] Reset password → new password works
- [ ] OAuth login (Google) → tokens returned
- [ ] OAuth login (Microsoft) → tokens returned
- [ ] Dashboard loads for authenticated user
- [ ] Stripe checkout → subscription created
- [ ] Account deletion → all data purged, 200 response
