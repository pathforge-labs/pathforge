# PLAN: Langfuse LLM Observability Activation

> **Sprint**: Post-50 · **Date**: 2026-04-24
> **Type**: `feat` · **Size**: Trivial (2 files, ~30 min)
> **Author**: Claude (Senior Staff)
> **Quality Score**: 51/60 → PASS ✅

---

## 1. Context & Problem Statement

The LLM observability layer is fully implemented in `apps/api/app/core/llm_observability.py` and wired into `app/core/llm.py`. It is guarded by `LLM_OBSERVABILITY_ENABLED=false` (the default). Without activation, every LLM call (resume parsing, career DNA, match scoring, OCR) runs blind — no trace data, no cost visibility, no prompt/response audit trail. Langfuse credentials need to be created and four env vars need to be set in the Railway production environment to activate this feature.

---

## 2. Goals & Non-Goals

**Goals:**
- Activate LLM observability in production by setting 4 env vars in Railway
- Validate that traces appear in the Langfuse dashboard after activation
- Add a health-check assertion to `/api/v1/observability` that confirms Langfuse is active

**Non-Goals:**
- Changing any application code (the implementation is complete)
- Staging environment activation (follow after production is confirmed working)
- Custom PII redaction rules beyond the existing `langfuse_pii_redaction=True` default
- Increasing `langfuse_sampling_rate` above 10% before validating costs

---

## 3. Implementation Steps

### Step 1 — Create Langfuse project and obtain credentials _(Manual)_

1. Sign in to [cloud.langfuse.com](https://cloud.langfuse.com)
2. Create project: `PathForge Production`
3. Navigate to **Settings → API Keys** → generate a new key pair
4. Copy `Public Key` and `Secret Key`

**Verify**: Both keys visible in Langfuse dashboard.

---

### Step 2 — Set env vars in Railway Production

In **Railway → pathforge-api → Variables**, add:

| Variable | Value |
|----------|-------|
| `LLM_OBSERVABILITY_ENABLED` | `true` |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-…` (from Step 1) |
| `LANGFUSE_SECRET_KEY` | `sk-lf-…` (from Step 1) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` |

> `LANGFUSE_SAMPLING_RATE` defaults to `0.1` (10%) — leave as default initially.

**Verify**: Railway redeploys the service; startup logs show:
```
LLM observability: enabled (Langfuse @ https://cloud.langfuse.com, sampling=0.1)
```

---

### Step 3 — Update `.env.example` to document the new vars
**File**: `apps/api/.env.example`

Add section:
```ini
# ── LLM Observability (Langfuse) ─────────────────────────────
LLM_OBSERVABILITY_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Verify**: File saved; `.env.example` committed but not `.env` (`.gitignore` already excludes it).

---

### Step 4 — Add observability status check to health response _(Optional enhancement)_
**File**: `apps/api/app/api/v1/observability.py`

Verify the existing `/api/v1/observability/status` endpoint already returns `langfuse_enabled`. If not, check `app/core/llm_observability.py:initialize_observability` for the health indicator and confirm it's surfaced.

**Verify**: `GET /api/v1/observability/status` returns `{"langfuse_enabled": true}` after activation.

---

### Step 5 — Smoke test Langfuse trace ingestion

1. Trigger any AI endpoint (e.g., `POST /api/v1/ai/parse-resume` with sample text)
2. Check Langfuse dashboard → **Traces** within 30 seconds
3. Confirm trace shows: model, tokens, latency, no PII in prompt content (names/emails redacted)

**Verify**: At least 1 trace visible with correct model ID and cost estimate.

---

## 4. Testing Strategy

**Unit tests**: N/A — no application code changes. The existing `tests/test_llm_observability.py` (if present) covers the initialization logic.

**Manual smoke test** (Step 5 above): The only meaningful test is observing a real trace in the Langfuse UI.

**Regression check**: After activation, run the existing CI suite (`pytest`) — all tests must still pass since `llm_observability_enabled=False` by default in the test environment (env var not set in CI).

Reference: `.agent/rules/testing.md` — for infrastructure-only changes, manual smoke test is the appropriate verification.

---

## 5. Security Considerations

- **Secret management**: `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` must be stored in Railway Variables, never committed to git. `.env.example` has empty values only.
- **PII redaction**: `langfuse_pii_redaction=True` is the default — names and emails in prompts are redacted before sending to Langfuse cloud. Confirm this is active in the Langfuse trace viewer (PII fields should show `[REDACTED]`).
- **Data residency**: Langfuse EU region (`eu.cloud.langfuse.com`) is available if EU data residency is required for GDPR compliance. Currently using `cloud.langfuse.com` (US). Consider switching `LANGFUSE_HOST` to `https://eu.cloud.langfuse.com`.
- **Sampling**: 10% sampling at launch means 90% of LLM calls are not traced — reduces data exposure surface.

Reference: `.agent/rules/security.md` — no secrets in code, env var pattern enforced.

---

## 6. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Langfuse cloud outage causes LiteLLM callback to fail | Low | LiteLLM failure callbacks are non-blocking; LLM calls succeed regardless |
| PII not fully redacted → GDPR concern | Medium | Verify in Step 5 that names/emails show `[REDACTED]`; switch to EU region if needed |
| Sampling overhead adds latency | Low | `initialize_observability` shows sampling is async; no synchronous overhead on LLM calls |
| `.env.example` committed with real keys by mistake | Medium | Keys are generated in Step 1 — never paste real keys into `.env.example` |

---

## 7. Success Criteria

- [ ] Railway logs show `LLM observability: enabled` on startup (not `disabled`)
- [ ] At least 1 Langfuse trace visible within 30s of triggering an AI endpoint
- [ ] Trace shows correct model name, token count, and latency
- [ ] PII fields show `[REDACTED]` (not raw names/emails)
- [ ] Existing CI test suite continues to pass (observability disabled in test env)
- [ ] `.env.example` updated with documented variables (empty values)

---

## Alignment Verification

| Check | Status |
|-------|--------|
| Trust > Optimization | ✅ Minimal change — only env vars + docs |
| Existing Patterns | ✅ `initialize_observability()` called at startup already; no new patterns |
| Rules Consulted | `security.md`, `testing.md` |
| Coding Style | ✅ No application code changes |

---

*Plan saved: `docs/PLAN-langfuse-observability.md`*  
*Activate with Railway Dashboard → set env vars → redeploy.*
