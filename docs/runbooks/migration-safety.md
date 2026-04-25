# Alembic Migration Safety Runbook

> **Sprint 36 WS-2** | PathForge Database Migration Procedure
> Last updated: 2026-03-03

---

## Overview

PathForge uses Alembic for database schema migrations with PostgreSQL (asyncpg driver). All migrations must follow this procedure to ensure data safety.

## Pre-flight Checklist

- [ ] Migration file reviewed and approved in PR
- [ ] `alembic_verify.py --sql-only` passes in CI
- [ ] No `DROP TABLE` or `DROP COLUMN` without explicit approval
- [ ] Downgrade function is implemented and tested
- [ ] Related application code is deployed and backward-compatible

---

## Local Development

```bash
# Generate a new migration
cd apps/api
alembic revision --autogenerate -m "description"

# Apply locally
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Verify full lifecycle
python scripts/alembic_verify.py
```

## Staging Deployment

```bash
# 1. Verify current state
alembic current

# 2. Preview SQL (dry run)
alembic upgrade head --sql

# 3. Apply migration
alembic upgrade head

# 4. Verify application
alembic current
```

## Production Deployment

> [!CAUTION]
> Production migrations require an explicit backup gate.

### Step 1: Create Database Backup

```bash
# Railway PostgreSQL
railway run pg_dump -Fc -f backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup is not empty
ls -la backup_*.dump
```

### Step 2: Run Backup Gate

```bash
DATABASE_BACKUP_CONFIRMED=true python scripts/alembic_backup_check.py
```

### Step 3: Apply Migration

```bash
alembic upgrade head
```

### Step 4: Verify

```bash
# Check current revision
alembic current

# Run application health check
curl -s https://api.pathforge.eu/api/v1/health | jq .
```

---

## Rollback Procedure

> [!WARNING]
> Always rollback one revision at a time to maintain consistency.

```bash
# Rollback one revision
alembic downgrade -1

# Verify current state
alembic current

# If rollback fails, restore from backup:
pg_restore -d $DATABASE_URL backup_YYYYMMDD_HHMMSS.dump
```

---

## CI Integration

The CI pipeline runs migration validation automatically:

- **`migration-check` job**: `alembic upgrade head --sql` (SQL-only, no DB)
- Validates migration files produce valid PostgreSQL SQL
- Blocks merge on syntax errors

---

## Troubleshooting

| Issue                               | Solution                                                       |
| :---------------------------------- | :------------------------------------------------------------- |
| "Target database is not up to date" | Run `alembic upgrade head` first                               |
| "Can't locate revision"             | Check `versions/` directory for missing files                  |
| "Drift detected"                    | Run `alembic revision --autogenerate` to capture model changes |
| Downgrade fails                     | Check the downgrade function in the migration file             |
| Backup gate blocks                  | Set `DATABASE_BACKUP_CONFIRMED=true` after creating backup     |
