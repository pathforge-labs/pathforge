# Architecture Decision Records (ADRs)

This directory captures architectural decisions made on PathForge. Each ADR is
an immutable, append-only document describing **one** decision in the context
that produced it — useful years later when the reasoning is no longer obvious
from the code.

## Why ADRs

Code shows *what* the system does. Git history shows *what changed*. Neither
explains *why* a design was chosen over plausible alternatives. ADRs close that
gap for decisions that are expensive to revisit: schema shape, auth posture,
transport security, sync/async boundaries, vendor selection, etc.

We do **not** write ADRs for routine implementation choices (naming, style,
refactors), PR-level decisions that commit messages already cover, or anything
reversible in under an hour.

## Filename convention

```
NNNN-kebab-case-title.md
```

- `NNNN` is a zero-padded, strictly increasing sequence. Never renumber.
- The title is the decision, not the problem (e.g. `0001-database-ssl-secure-by-default.md`,
  not `0001-fix-database-tls-gap.md`).

## Status lifecycle

- `Proposed` — under review, not yet merged.
- `Accepted` — merged and in effect.
- `Superseded by ADR-NNNN` — replaced; keep the file, add a link forward.
- `Deprecated` — no longer in effect; keep for historical reference.

Never delete an ADR. When a decision is reversed, write a new ADR that
supersedes it.

## Template

Every ADR follows the same skeleton:

```markdown
# ADR-NNNN: <Decision>

- **Status**: Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- **Date**: YYYY-MM-DD
- **Deciders**: <names/roles>
- **Context links**: <issues, audits, runbooks, prior ADRs>

## Context
What forces are at play — technical, business, regulatory, operational.

## Decision
The decision, stated plainly, in present tense.

## Alternatives Considered
Each alternative with a one-paragraph rationale for rejection.

## Consequences
- Positive: …
- Negative / trade-offs: …
- Operational impact: …

## Verification
How we confirm the decision is in effect and catch regressions.

## References
Links to code, tests, runbooks, external docs.
```

## Index

| # | Title | Status |
|:--|:--|:--|
| [0001](0001-database-ssl-secure-by-default.md) | Database SSL secure-by-default with production guard | Accepted |
| [0002](0002-redis-ssl-secure-by-default.md) | Redis SSL secure-by-default with production guard and scheme reconciliation | Accepted |
