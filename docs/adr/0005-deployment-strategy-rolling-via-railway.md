# ADR-0005: Deployment Strategy — Rolling via Railway (canary/blue-green deferred)

- **Status**: Accepted
- **Date**: 2026-04-23
- **Deciders**: Emre Dursun (owner)
- **Sprint 44 item**: P3-1 — Canary / blue-green deployment strategy evaluation

---

## Context

PathForge API is deployed on Railway. The current deploy pipeline (`deploy.yml`) uses Railway's native deployment mechanism: push a new Docker image, Railway replaces the running container. The pipeline includes a pre-flight validation step and a post-deploy health check with a rollback instruction; rollback is manual via the Railway dashboard.

As the service approaches launch, the question is: should we implement canary deployments or blue-green deployments instead of the current rolling replacement?

**Traffic profile at launch:**
- Expected early-stage: ≤100 concurrent users
- No contractual SLA; best-effort uptime
- Single Railway service (one replica in free/hobby tier)
- No external load balancer we control

**Current downtime window:** Railway's rolling replace takes ~15–30 s during which the old container terminates and the new one starts. Railway's health check (`/api/v1/health/ready`) must return 200 before traffic is switched.

---

## Decision

**Continue with Railway's native rolling deployment for now. Defer canary and blue-green deployments.**

The rollout window is accepted as a startup trade-off. Neither canary nor blue-green is adopted at this stage.

---

## Reasoning

### Why not canary?

Canary deployments split a fraction of live traffic to the new version before full rollout. They require:
1. A **load balancer** that supports weighted routing (e.g., Nginx, Cloudflare, AWS ALB, or a Railway Teams feature)
2. **Multiple replicas** of the API running simultaneously — one "stable" and one "canary"
3. **Observability** (Sentry, Langfuse, structured error rate metrics) to evaluate the canary's health

Railway's hobby tier runs a single replica and does not expose weighted routing controls. Even on Teams, the routing granularity is insufficient for small user counts (splitting 10 users 90/10 is meaningless). Sentry and Langfuse are not yet live (OPS-1 and N-5 blocked on OPS-3). Canary provides little value without the observability stack to measure it.

**Revisit trigger**: ≥500 DAU **and** Sentry + Langfuse active.

### Why not blue-green?

Blue-green deployments maintain two identical production environments and switch DNS/LB at cutover. They require:
1. A **second Railway service** (doubles cost: compute + postgres replica or shared DB)
2. **Stateless API** — PathForge IS stateless (JWT-based auth, no server-side session), so this box is ticked
3. Database schema compatibility between old and new — Alembic migrations must be backward-compatible for the duration of the switch
4. DNS/LB switching capability — not available on Railway without custom domain + Cloudflare proxy

On hobby/starter tier, provisioning a second environment that mirrors production is costly and operationally complex for a team of one. The staging environment (N-4) is not yet live either, so there is no "warm" second environment to promote.

**Revisit trigger**: Railway staging environment live (N-4) **and** traffic ≥ 1000 DAU.

### Why rolling is acceptable now

- Railway's health check (`/api/v1/health/ready` → DB + Redis) ensures the new container is healthy before traffic switches. An unhealthy deploy is caught within the health check timeout (≤ 60 s), not after users hit errors.
- The `deploy.yml` post-deploy step polls `/api/v1/health/ready` and marks the workflow failed if it doesn't return 200 within 5 minutes. This surfaces broken deploys immediately.
- Rollback is manual but fast: Railway dashboard → "Redeploy previous" → ~30 s.
- At ≤100 concurrent users, a 15–30 s rolling window affects at most a handful of in-flight requests. These will receive a `502` from Railway's ingress, which clients retry.
- `deploy.yml` has `concurrency: cancel-in-progress: false` — deploys never overlap.

---

## Alternatives considered

| Strategy | Verdict | Blocking condition |
| :--- | :--- | :--- |
| **Canary** | Deferred | Needs multi-replica + LB weighted routing + Sentry/Langfuse live |
| **Blue-green** | Deferred | Needs 2nd Railway service + N-4 staging live + DB migration discipline |
| **Feature flags** (GrowthBook) | Out of scope | Addresses feature rollout, not deployment risk |
| **Rolling (current)** | **Accepted** | Already in place; health check gates traffic switch |

---

## Consequences

- Accept ≤30 s potential downtime per deploy (mitigated by Railway health check)
- Rollback remains manual via Railway dashboard (documented in `docs/runbooks/production-checklist.md`)
- When re-evaluating, the first step is enabling the Railway staging environment (N-4), which doubles as the blue-green "inactive" environment
- The Alembic migration discipline (backward-compatible migrations, `alembic upgrade head` before traffic switch) must be maintained regardless of deployment strategy

---

## Verification

| Check | Evidence |
| :--- | :--- |
| Health check guards traffic switch | `deploy.yml` — post-deploy step polls `/api/v1/health/ready` |
| Deploy never overlaps | `concurrency: cancel-in-progress: false` in `deploy.yml` |
| Rollback documented | `docs/runbooks/production-checklist.md` §"Rollback" |
| Revisit triggers documented | This ADR §"Why not canary" and §"Why not blue-green" |
