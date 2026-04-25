# Runbook: LLM Budget Exceeded

> **Severity**: P2 — AI features degraded
> **Owner**: Backend / AI
> **Last Updated**: 2026-03-19

## Symptoms

- AI endpoints (Career DNA, Threat Radar, Salary Intelligence) return errors
- Sentry: `LLMError` with "Monthly budget exceeded" message
- Redis key `llm:monthly_cost:{YYYY-MM}` exceeds `LLM_MONTHLY_BUDGET_USD`
- Users report "Career DNA analysis failed" or similar

## Impact

All AI-powered features stop working. Core user flows (resume analysis, career intelligence) are blocked. Non-AI features (auth, billing, profile management) continue normally.

## Current Budget Configuration

```python
# config.py
llm_monthly_budget_usd = 200.0  # Default $200/month
llm_primary_rpm = 60            # Claude Sonnet 4
llm_fast_rpm = 200              # Gemini Flash 2.0
llm_deep_rpm = 10               # Claude (deep analysis)
```

## Diagnosis

```bash
# Check current month's spending via Redis
# (requires Redis CLI access or API admin endpoint)
curl https://api.pathforge.eu/api/v1/admin/system-health \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.llm_costs'

# Check Railway logs for budget warnings
railway logs --service api | grep -i "budget\|cost\|exceeded"
```

## Resolution

### 1. Temporary Budget Increase

```bash
# Increase budget for current month
railway variables set LLM_MONTHLY_BUDGET_USD=300
railway restart --service api
```

### 2. Investigate Cost Spike

- Check Anthropic Console (console.anthropic.com) → Usage
- Check Google AI Studio (aistudio.google.com) → Usage
- Look for abnormal patterns: repeated failures causing retries, single user abuse

### 3. If Under Attack / Abuse

```bash
# Identify heavy users via logs
railway logs --service api | grep "career_dna\|threat_radar" | sort | uniq -c | sort -rn

# Block abusive user via admin endpoint
curl -X PATCH https://api.pathforge.eu/api/v1/admin/users/{user_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"is_active": false}'
```

## Prevention

- Budget guard resets automatically on the 1st of each month (Redis TTL)
- Per-endpoint rate limits (Career DNA: 3/min) prevent individual abuse
- Configure Sentry alert when spending reaches 80% of budget
- Monitor Anthropic/Google usage dashboards weekly
