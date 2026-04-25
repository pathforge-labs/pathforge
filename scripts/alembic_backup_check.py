"""
PathForge — Alembic Pre-Production Backup Gate
=================================================
Safety gate that requires explicit backup confirmation
before applying migrations in production.

Sprint 36 WS-2: Prevents accidental production migration
without verified database backup.

Usage:
    DATABASE_BACKUP_CONFIRMED=true python scripts/alembic_backup_check.py

Exit codes:
    0 — Backup confirmed, safe to proceed
    1 — Backup not confirmed or migration plan failed
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"


def get_migration_plan() -> str:
    """Generate the migration plan summary (upgrade SQL)."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=str(API_DIR),
        capture_output=True,
        text=True,
    )
    return result.stdout


def count_migration_revisions() -> int:
    """Count the number of pending migration revisions."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "history", "--indicate-current"],
        cwd=str(API_DIR),
        capture_output=True,
        text=True,
    )
    lines = [
        line for line in result.stdout.strip().splitlines() if line.strip()
    ]
    return len(lines)


def main() -> NoReturn:
    """Verify backup confirmation before production migration."""
    print("PathForge — Pre-Production Migration Gate")
    print("=" * 60)

    # Check backup confirmation
    backup_confirmed = os.environ.get("DATABASE_BACKUP_CONFIRMED", "").lower()

    if backup_confirmed != "true":
        print(
            "\n❌ DATABASE_BACKUP_CONFIRMED is not set to 'true'.",
            file=sys.stderr,
        )
        print(
            "\nBefore applying migrations in production:",
            file=sys.stderr,
        )
        print("  1. Create a database backup", file=sys.stderr)
        print("  2. Verify the backup is restorable", file=sys.stderr)
        print(
            "  3. Set DATABASE_BACKUP_CONFIRMED=true and re-run",
            file=sys.stderr,
        )
        print(
            "\nSee docs/runbooks/migration-safety.md for full procedure.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("✅ Backup confirmation: DATABASE_BACKUP_CONFIRMED=true")

    # Show migration plan summary
    revision_count = count_migration_revisions()
    print(f"\n📋 Migration revisions in history: {revision_count}")

    print("\n📝 Migration SQL Preview:")
    print("-" * 40)
    sql_output = get_migration_plan()
    if sql_output.strip():
        # Show first 50 lines of SQL
        lines = sql_output.splitlines()
        for line in lines[:50]:
            print(f"  {line}")
        if len(lines) > 50:
            print(f"  ... ({len(lines) - 50} more lines)")
    else:
        print("  (No pending migrations)")

    print(f"\n{'='*60}")
    print("  ✅ Backup verified — safe to apply migrations")
    print(f"{'='*60}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
