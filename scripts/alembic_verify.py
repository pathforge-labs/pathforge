"""
PathForge — Alembic Migration Verification Script
===================================================
Validates the full migration lifecycle in CI.

Steps:
    1. Assert Alembic version >= 1.13.0 (drift detection support)
    2. Run alembic upgrade head (apply all migrations)
    3. Run alembic downgrade base (rollback everything)
    4. Run alembic upgrade head (re-apply — proves reversibility)
    5. Run alembic check (drift detection — models vs migrations)

Usage:
    python scripts/alembic_verify.py

    # CI (with PostgreSQL service):
    DATABASE_URL=postgresql+asyncpg://... python scripts/alembic_verify.py

Exit codes:
    0 — All checks passed
    1 — Verification failed (details in stderr)

Audit H2: This is a Python script (not bash) for Windows compatibility.
Audit M3: Asserts Alembic >= 1.13.0 for drift detection support.
"""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import NoReturn

# Alembic working directory
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"


def run_command(args: list[str], description: str) -> None:
    """Run a command and abort if it fails."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        args,
        cwd=str(API_DIR),
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\n❌ FAILED: {description}", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ PASSED: {description}")


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


def main() -> NoReturn:
    """Run the full Alembic verification suite."""
    print("PathForge — Alembic Migration Verification")
    print("=" * 60)

    # Step 1: Version check
    check_alembic_version()

    # Step 2: Fresh upgrade
    run_command(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        "Upgrade: base → head",
    )

    # Step 3: Full rollback
    run_command(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        "Downgrade: head → base",
    )

    # Step 4: Re-apply (proves reversibility)
    run_command(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        "Re-upgrade: base → head (reversibility proof)",
    )

    # Step 5: Drift detection
    run_command(
        [sys.executable, "-m", "alembic", "check"],
        "Drift detection: models vs migrations",
    )

    print(f"\n{'='*60}")
    print("  ✅ All Alembic verification checks passed!")
    print(f"{'='*60}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
