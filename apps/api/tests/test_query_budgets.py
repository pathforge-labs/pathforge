"""Render the per-route query-budget registry as a Markdown table.

Acts as a CI artefact: reviewers can read ``query-budget-report.md``
to see, per route, the declared budget and the maximum count observed
across the suite. Routes whose observed count is at-or-above their
declared budget are flagged so reviewers know the headroom is gone.

The fixture lives in ``tests/conftest.py`` (T2 / ADR-0007).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Re-import the same registry the autouse fixture writes into so the
# table reflects the full suite's observations, not just this module's.
from tests.conftest import _query_budget_registry

# Mark the file so pytest can collect, but no test inside drives a
# request — there is no budget overage path to trip our own gate.
pytestmark = pytest.mark.no_query_budget


def test_query_budget_registry_renders_to_markdown(tmp_path: Path) -> None:
    """Render the registry into a sortable Markdown table.

    Always passes — the goal is to *produce* the report, not gate the
    suite on its contents (the autouse fixture already gates on
    overage).  CI uploads the resulting file as an artefact via
    ``actions/upload-artifact@v4`` (workflow change tracked in T2).
    """
    if not _query_budget_registry:
        pytest.skip(
            "Registry empty — no annotated route was exercised in this run."
        )

    rows = sorted(
        _query_budget_registry.items(),
        key=lambda item: (item[1][0] - item[1][1], item[0]),  # tightest first
    )

    lines = [
        "# Per-route Query Budget Report",
        "",
        "| Endpoint | Declared | Max observed | Headroom | Flag |",
        "|:---|:---:|:---:|:---:|:---:|",
    ]
    for endpoint, (declared, observed) in rows:
        headroom = declared - observed
        flag = "⚠️ at-limit" if headroom <= 0 else ""
        lines.append(
            f"| `{endpoint}` | {declared} | {observed} | {headroom} | {flag} |"
        )

    report = "\n".join(lines) + "\n"
    out_path = tmp_path / "query-budget-report.md"
    out_path.write_text(report, encoding="utf-8")

    # Echo to a known path the CI workflow can pick up.
    ci_artefact_dir = os.environ.get("PATHFORGE_QUERY_BUDGET_ARTEFACT_DIR")
    if ci_artefact_dir:
        ci_dir = Path(ci_artefact_dir)
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "query-budget-report.md").write_text(
            report, encoding="utf-8"
        )

    # Sanity assertions on the rendered table itself — caught at this
    # layer so the artefact uploader doesn't ship a broken file.
    assert "# Per-route Query Budget Report" in report
    assert "Declared" in report
    assert "Max observed" in report
    assert all(
        f"`{endpoint}`" in report for endpoint in _query_budget_registry
    )
