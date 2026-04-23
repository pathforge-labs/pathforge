# PathForge — Staging Environment Setup (N-4)

> **One-time setup guide.** After completing this guide, `deploy-staging.yml`
> auto-deploys every push to `main` and the `visual-regression` CI job gains a
> stable target for VR baselines.
>
> **Time estimate**: ~30 minutes (mostly Railway dashboard + copy-paste).

---

## 1. Create the Railway staging service

1. Open [railway.app](https://railway.app) → your PathForge project.
2. Click **+ New** → **Empty Service** → name it `pathforge-api-staging`.
3. In the new service, **Settings → Source**: point to the same GitHub repo,
   branch `main` (staging always tracks `main`; production tracks `production`).
4. In **Settings → Deploy**: set the same Dockerfile path as production
   (`docker/Dockerfile.api`).

---

## 2. Copy environment variables from production

The staging service needs all the same env vars as production **except** for a
few overrides listed below.

**Quick copy**: Railway Dashboard → production service → **Variables** →
**⋯ → Copy all to…** → select `pathforge-api-staging`.

Then override the following:

| Variable | Production value | Staging override |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | `staging` |
| `DATABASE_URL` | prod Supabase URL | staging Supabase URL (see §3) |
| `REDIS_URL` | prod Redis URL | separate staging Redis (see §4) |
| `RATELIMIT_STORAGE_URI` | prod Redis URL | staging Redis URL |
| `CORS_ORIGINS` | `https://pathforge.eu` | `https://staging.pathforge.eu,http://localhost:3000` |
| `STRIPE_SECRET_KEY` | `sk_live_…` | `sk_test_…` (keep test mode on staging) |
| `STRIPE_WEBHOOK_SECRET` | live webhook secret | test webhook secret |
| `SENTRY_DSN` | prod DSN | optional — same DSN with `environment=staging` tag auto-set |

---

## 3. Staging database

**Option A (recommended for now — shared Supabase project, separate schema):**

Use the same Supabase project as production but with a `staging` schema prefix:
```
DATABASE_URL=postgresql+asyncpg://...<same creds>...?options=--search_path=staging,public
```
Run `alembic upgrade head` against the staging schema after setup (see §6).

**Option B (isolated — Railway Postgres plugin):**

In the staging service, click **+ Add Plugin** → **PostgreSQL**. Railway
auto-injects `DATABASE_URL`. This gives full isolation but costs more and
requires a full DB setup.

---

## 4. Staging Redis

In the staging service, click **+ Add Plugin** → **Redis**. Railway auto-injects
`REDIS_URL`. Set:
```
RATELIMIT_STORAGE_URI=$REDIS_URL
```

---

## 5. Note the staging service ID

Railway Dashboard → `pathforge-api-staging` service → **Settings → General** →
copy the **Service ID** (UUID format).

Go to GitHub → your repo → **Settings → Secrets and variables → Actions**:
- Add **Secret**: `RAILWAY_STAGING_SERVICE_ID` = the UUID from above.
- Add **Variable**: `STAGING_API_URL` = `https://<staging-hostname>.up.railway.app`
  (find the hostname in Railway → staging service → **Settings → Networking**).

---

## 6. Run Alembic on staging DB

In Railway Dashboard → `pathforge-api-staging` → **Shell** (or via Railway CLI):
```bash
alembic upgrade head
```
Confirm: `alembic current` shows the latest revision.

---

## 7. Verify the workflow

Push any trivial commit to `main` (or trigger manually):
**GitHub Actions → Deploy (Staging) → should turn green.**

Then confirm:
```bash
curl https://<staging-hostname>.up.railway.app/api/v1/health/ready | jq .
```
Expected: `"status": "healthy"`, `"db": {"connected": true, "ssl": true}`.

---

## 8. Connect Vercel web previews to staging API (optional)

In Vercel → `pathforge-web` project → **Settings → Environment Variables**:
- Add `NEXT_PUBLIC_API_URL = https://<staging-hostname>.up.railway.app` for
  **Preview** environments (branch: `main`).

This wires Vercel preview deployments to the staging API.

---

## Verification gate (N-4 done when)

- [ ] `deploy-staging.yml` runs green on `main` push
- [ ] `https://<staging>/api/v1/health/ready` → 200, `db.ssl: true`
- [ ] `alembic current` on staging DB → latest revision
- [ ] `STAGING_API_URL` variable set in GitHub Actions
