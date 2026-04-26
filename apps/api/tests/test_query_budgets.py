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

# Re-import the same registries the autouse fixture writes into so the
# table reflects the full suite's observations, not just this module's.
from tests.conftest import (
    _query_budget_registry,
    _unannotated_query_observations,
)

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
    if not _query_budget_registry and not _unannotated_query_observations:
        pytest.skip("Registry + inventory both empty — no route was exercised in this run.")

    annotated_rows = sorted(
        _query_budget_registry.items(),
        key=lambda item: (item[1][0] - item[1][1], item[0]),  # tightest first
    )
    inventory_rows = sorted(
        _unannotated_query_observations.items(),
        key=lambda item: (-item[1], item[0]),  # largest observed first
    )

    lines = [
        "# Per-route Query Budget Report",
        "",
        "## Annotated routes (declared vs observed)",
        "",
        "| Endpoint | Declared | Max observed | Headroom | Flag |",
        "|:---|:---:|:---:|:---:|:---:|",
    ]
    if annotated_rows:
        for endpoint, (declared, observed) in annotated_rows:
            headroom = declared - observed
            flag = "⚠️ at-limit" if headroom <= 0 else ""
            lines.append(f"| `{endpoint}` | {declared} | {observed} | {headroom} | {flag} |")
    else:
        lines.append("| _no annotated routes exercised_ | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Unannotated routes (inventory for T2-rollout)",
            "",
            "Routes touched by the suite that have no `@route_query_budget` "
            "yet.  Recommended budget = `max_observed + ceil(max_observed * 0.2)` "
            "(20% headroom rounded up).",
            "",
            "| Endpoint | Max observed | Recommended budget |",
            "|:---|:---:|:---:|",
        ]
    )
    if inventory_rows:
        import math

        # Recommended budget = max(default=4, max_observed + 20% headroom).
        # The 4-query floor protects un-measured or low-traffic handlers
        # whose auth-dependency chain alone routinely runs 3-4 queries
        # (token decode + user lookup + tier check + audit). Routes that
        # observed zero queries during the suite would otherwise be
        # recommended a budget of 1, which is brittle the moment a real
        # auth-bearing test path exercises them.
        default_floor = 4
        for endpoint, observed in inventory_rows:
            with_headroom = observed + max(1, math.ceil(observed * 0.2))
            recommended = max(default_floor, with_headroom)
            lines.append(f"| `{endpoint}` | {observed} | {recommended} |")
    else:
        lines.append("| _all touched routes are annotated_ | — | — |")

    report = "\n".join(lines) + "\n"
    out_path = tmp_path / "query-budget-report.md"
    out_path.write_text(report, encoding="utf-8")

    # Echo to a known path the CI workflow can pick up.
    ci_artefact_dir = os.environ.get("PATHFORGE_QUERY_BUDGET_ARTEFACT_DIR")
    if ci_artefact_dir:
        ci_dir = Path(ci_artefact_dir)
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "query-budget-report.md").write_text(report, encoding="utf-8")

    # Sanity assertions on the rendered table itself — caught at this
    # layer so the artefact uploader doesn't ship a broken file.
    assert "# Per-route Query Budget Report" in report
    assert "Declared" in report
    assert "Max observed" in report
    assert all(f"`{endpoint}`" in report for endpoint in _query_budget_registry)
    assert all(f"`{endpoint}`" in report for endpoint in _unannotated_query_observations)
