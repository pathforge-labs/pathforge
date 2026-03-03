"""
PathForge — Alembic Migration Verification Script
===================================================
Validates the full migration lifecycle in CI.

Steps:
    0. Print current migration state (alembic current)
    1. Assert Alembic version >= 1.13.0 (drift detection support)
    2. Run alembic upgrade head (apply all migrations)
    3. Run alembic downgrade base (rollback everything)
    4. Run alembic upgrade head (re-apply — proves reversibility)
    5. Run alembic check (drift detection — models vs migrations)

Usage:
    python scripts/alembic_verify.py             # Full lifecycle
    python scripts/alembic_verify.py --check-only # CI gate: fail if pending migrations
    python scripts/alembic_verify.py --sql-only   # Generate SQL without DB connection

Exit codes:
    0 — All checks passed
    1 — Verification failed (details in stderr)

Sprint 36 WS-2: Added Step 0, --check-only, --sql-only flags.
Audit H2: This is a Python script (not bash) for Windows compatibility.
Audit M3: Asserts Alembic >= 1.13.0 for drift detection support.
Audit F4: --sql mode for CI (no DB needed, validates PG-specific SQL).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import NoReturn

# Alembic working directory
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"


def run_command(
    args: list[str], description: str, *, allow_failure: bool = False
) -> int:
    """Run a command and abort if it fails (unless allow_failure=True)."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        args,
        cwd=str(API_DIR),
        capture_output=False,
    )

    if result.returncode != 0 and not allow_failure:
        print(f"\n❌ FAILED: {description}", file=sys.stderr)
        sys.exit(1)

    if result.returncode == 0:
        print(f"\n✅ PASSED: {description}")
    else:
        print(f"\n⚠️  SKIPPED/WARN: {description}")

    return result.returncode


def check_alembic_version() -> None:
    """Assert Alembic >= 1.13.0 (required for 'alembic check')."""
    try:
        alembic_version = pkg_version("alembic")
    except Exception:
        print("❌ Alembic not installed", file=sys.stderr)
        sys.exit(1)

    parts = alembic_version.split(".")
    major, minor = int(parts[0]), int(parts[1])

    if (major, minor) < (1, 13):
        print(
            f"❌ Alembic {alembic_version} found, but >= 1.13.0 is required "
            f"for drift detection ('alembic check')",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"✅ Alembic version: {alembic_version} (>= 1.13.0)")


def run_check_only() -> NoReturn:
    """CI gate: fail if there are pending (unapplied) migrations."""
    print("\nPathForge — Alembic Check-Only (CI Gate)")
    print("=" * 60)

    check_alembic_version()

    # Show current state
    run_command(
        [sys.executable, "-m", "alembic", "current"],
        "Step 0: Current migration state",
        allow_failure=True,
    )

    # Check for pending migrations
    returncode = run_command(
        [sys.executable, "-m", "alembic", "check"],
        "Check: Verify no pending migrations",
        allow_failure=True,
    )

    if returncode != 0:
        print(
            "\n❌ Pending migrations detected. Run 'alembic upgrade head' "
            "to apply before merging.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  ✅ No pending migrations — safe to merge")
    print(f"{'='*60}\n")
    sys.exit(0)


def run_sql_only() -> NoReturn:
    """Generate migration SQL without DB connection (CI validation)."""
    print("\nPathForge — Alembic SQL-Only (No DB Required)")
    print("=" * 60)

    check_alembic_version()

    # Generate upgrade SQL to validate syntax (PostgreSQL dialect)
    run_command(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        "SQL Generation: Validate migration SQL (PG dialect)",
    )

    print(f"\n{'='*60}")
    print("  ✅ Migration SQL generation passed")
    print(f"{'='*60}\n")
    sys.exit(0)


def main() -> NoReturn:
    """Run the full Alembic verification suite."""
    parser = argparse.ArgumentParser(
        description="PathForge Alembic Migration Verification"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="CI gate: fail if pending migrations exist",
    )
    parser.add_argument(
        "--sql-only",
        action="store_true",
        help="Generate SQL without DB connection (validates syntax)",
    )
    args = parser.parse_args()

    if args.check_only:
        run_check_only()

    if args.sql_only:
        run_sql_only()

    # Full lifecycle verification
    print("PathForge — Alembic Migration Verification (Full)")
    print("=" * 60)

    # Step 0: Current state (Sprint 36 WS-2 / Audit F5)
    run_command(
        [sys.executable, "-m", "alembic", "current"],
        "Step 0: Current migration state",
        allow_failure=True,
    )

    # Step 1: Version check
    check_alembic_version()

    # Step 2: Fresh upgrade
    run_command(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        "Step 2: Upgrade base → head",
    )

    # Step 3: Full rollback
    run_command(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        "Step 3: Downgrade head → base",
    )

    # Step 4: Re-apply (proves reversibility)
    run_command(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        "Step 4: Re-upgrade base → head (reversibility proof)",
    )

    # Step 5: Drift detection
    run_command(
        [sys.executable, "-m", "alembic", "check"],
        "Step 5: Drift detection (models vs migrations)",
    )

    print(f"\n{'='*60}")
    print("  ✅ All Alembic verification checks passed!")
    print(f"{'='*60}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()

