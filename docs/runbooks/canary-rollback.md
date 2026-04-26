# Canary Rollback Runbook

> **T5 / Sprint 57 / [ADR-0009](../adr/0009-progressive-deployment-and-auto-rollback.md).**
> Manual override for the Sentry-driven auto-rollback path.

---

## TL;DR

| Symptom | First action |
|:---|:---|
| Sentry alert fired but the flag is still at `percent_5` / `percent_25` (auto-rollback didn't fire) | **§ 1 — Manual rollback** |
| Auto-rollback fired but you believe the alert was a false positive | **§ 2 — Re-enable after false alarm** |
| Webhook receiver is 401-ing every request | **§ 3 — Sentry signing-secret reset** |
| Flag is at `internal_only` but new users keep landing on the new code path | **§ 4 — Fail-closed audit** |

---

## 1. Manual rollback

Use when the auto-rollback **didn't fire** but you've seen enough
to want the new build off production.

```bash
# 1. Verify current stage (read-only).
curl -s https://api.pathforge.eu/api/v1/internal/feature-flags/<flag_key> \
  -H "X-Admin-Token: $PATHFORGE_ADMIN_TOKEN" | jq .

# 2. Roll back via the same webhook the Sentry alert would call.
#    Compute the HMAC manually so you don't depend on Sentry going
#    through with the alert.
BODY='{
  "data": {
    "metric": {"name": "p0_user_rate", "value": 1.0},
    "tags": {"feature_flag": "<flag_key>"}
  }
}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SENTRY_WEBHOOK_SECRET" | awk '{print $2}')
curl -s -X POST https://api.pathforge.eu/api/v1/internal/sentry/auto-rollback \
  -H "Content-Type: application/json" \
  -H "Sentry-Hook-Signature: $SIG" \
  -d "$BODY" | jq .
```

Expected response: `{"rolled_back": true, "flag_key": "<flag_key>", ...}`.

> **Tip.** Once GrowthBook is provisioned, the manual path will be a
> dashboard click instead of a curl. Keep this runbook updated when
> that lands.

---

## 2. Re-enable after false alarm

After auto-rollback has flipped the flag to `internal_only`, a
re-enable kicks off a **fresh 24 h paying-user delay window** for
major releases. Do not skip steps:

1. Confirm root cause of the alert. If genuinely a flap (e.g. one
   noisy CDN error spike), document in the incident channel.
2. Increase the alert threshold or add a noise filter in Sentry —
   **fix the alert before re-enabling**, not after.
3. Promote the flag back to its prior stage:
   ```bash
   # GrowthBook dashboard: edit flag → set rollout to 5 % (or 25 %).
   # In-memory provider (pre-GrowthBook): no manual API; redeploy with
   # the desired stage seeded in app/core/feature_flags.py.
   ```
4. Watch Sentry for 30 min before promoting to the next stage.

---

## 3. Sentry signing-secret reset

If the Sentry webhook receiver is 401-ing every request:

1. **Verify the secret is set in Railway** —
   `railway variables --service api | grep SENTRY_WEBHOOK_SECRET`.
   Empty → fail-closed (every webhook rejected).
2. **Verify Sentry side** — Settings → Integrations → Webhooks →
   confirm the secret matches.
3. **Rotate** if either side has drifted:
   ```bash
   NEW_SECRET=$(openssl rand -hex 32)
   railway variables set SENTRY_WEBHOOK_SECRET="$NEW_SECRET" --service api
   # Then update the secret in Sentry's webhook UI to the same value.
   ```
4. Send a synthetic alert from Sentry and confirm 200.

---

## 4. Fail-closed audit

`is_enabled()` is fail-closed: unknown flag → False. If a flag is at
`internal_only` but external users are still hitting the new code
path, one of these is true:

* **Code path doesn't actually consult `is_enabled`.** Grep the route
  for `is_enabled` calls. Any code that reads `feature_flags` only
  through `feature_gate` won't be gated by rollout stage.
* **Caller is using a stale provider instance.** Multi-worker
  deployments need the GrowthBook-backed provider; the in-memory
  one is per-process. Check `_get_provider()` returns
  `GrowthBookProvider` in production.
* **`is_internal=True` is set on the user.** Internal users are
  gate-bypass at every stage by design. Audit the user record.

---

## 5. After the incident

| Item | Owner | When |
|:---|:---|:---|
| Sentry alert tuned (raise threshold, add filter, or split into two alerts) | reso | Same day |
| Postmortem entry in `docs/operations/IR-PLAN.md` | belengaz | Within 48 h |
| Quality-gate check: did the canary correctly limit blast radius? Update `is_enabled` test coverage if a corner case was missed | tech lead | Next sprint |

## References

* [ADR-0009](../adr/0009-progressive-deployment-and-auto-rollback.md)
  — design + rationale
* `app/core/feature_flags.py` — flag system source
* `app/core/sentry_auto_rollback.py` — webhook receiver source
* `tests/test_feature_flags.py` + `tests/test_sentry_auto_rollback.py`
  — what the gates promise
