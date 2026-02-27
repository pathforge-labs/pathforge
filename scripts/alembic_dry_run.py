"""
PathForge — Alembic Dry-Run Script
====================================
Generates migration SQL without executing it.

Useful for reviewing production migration SQL before deploying.

Usage:
    python scripts/alembic_dry_run.py

    # Output SQL to file:
    python scripts/alembic_dry_run.py > migration.sql

Exit codes:
    0 — SQL generated successfully
    1 — Generation failed
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import NoReturn

# Alembic working directory
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"


def main() -> NoReturn:
    """Generate migration SQL without executing."""
    print("-- PathForge Alembic Dry-Run", file=sys.stderr)
    print(f"-- Working directory: {API_DIR}", file=sys.stderr)
    print("-- Generating SQL for: base → head\n", file=sys.stderr)

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=str(API_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ SQL generation failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Output SQL to stdout (can be piped to file)
    print(result.stdout)

    print("\n-- ✅ SQL generation complete", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
