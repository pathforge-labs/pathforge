---
description: Display project and progress status. Current state overview.
---

# /status — Project & Sprint Status Dashboard

> **Trigger**: `/status` (full) · `/status brief` · `/status health`
> **Lifecycle**: On-demand, any time during development

---

## 🔴 Critical Rules

1. **READ-ONLY** — this workflow only reads and reports, never modifies files
2. **REAL DATA** — all numbers come from source files, never estimated or invented
3. **ROADMAP is SSOT** — sprint progress comes from `docs/ROADMAP.md`

---

## Mode Detection

| Command          | Output                                        |
| :--------------- | :-------------------------------------------- |
| `/status`        | Full dashboard (all sections)                 |
| `/status brief`  | 1-line summary                                |
| `/status health` | Health gates only (lint, types, tests, build) |

---

## Steps

### Step 1: Load Data Sources

// turbo

Read and extract data from:

- `docs/ROADMAP.md` — current sprint definition, task status, Sprint Velocity table
- `.agent/session-context.md` — work done, P0 blockers, handoff notes
- `.agent/session-state.json` — production readiness score, test counts, gate results
- `docs/CHANGELOG.md` — recent shipped work
- `git status` — branch, uncommitted changes
- `git log -5 --oneline` — recent commits

**Edge case:** No active sprint → show "No active sprint" with last completed sprint summary.

### Step 2: Sprint Progress

// turbo

From ROADMAP sprint section, count:

- Total tasks: `[ ]` + `[x]` + `[-]` + `[/]`
- Completed: `[x]`
- In progress: `[/]`
- Deferred: `[-]`
- Remaining: `[ ]`
- Progress: `completed / total * 100`

### Step 3: Health Check (for `/status` and `/status health`)

// turbo

Run quick health gates:

```powershell
# Cwd: apps/api
& ".venv\Scripts\python.exe" -m ruff check app/ --quiet

# Cwd: apps/web
pnpm lint
npx tsc --noEmit
```

### Step 4: Velocity Trend

// turbo

From ROADMAP Sprint Velocity table, extract last 5 sprints:

| Sprint | Tasks | Sessions | Completed | Ad-Hoc |
| :----- | :---- | :------- | :-------- | :----- |
| {N-4}  | ...   | ...      | ...       | ...    |
| {N-3}  | ...   | ...      | ...       | ...    |
| {N-2}  | ...   | ...      | ...       | ...    |
| {N-1}  | ...   | ...      | ...       | ...    |
| {N}    | ...   | ...      | ...       | ...    |

---

## Output Format

### `/status` — Full Dashboard

```markdown
# PathForge Status

> Branch: {branch} · Sprint: {N} — {title} · {date}

## Sprint {N} Progress

{progress_bar} {completed}/{total} ({percent}%)

- ✅ Completed: {n}
- 🔄 In Progress: {n}
- ⏳ Remaining: {n}
- 📦 Deferred: {n}

## P0 Blockers

| #                                  | Blocker | Sprint |
| :--------------------------------- | :------ | :----- |
| {blockers from session-context.md} |

## Production Readiness

Score: {score}/100 · Verdict: {GO/NO-GO}

- P0: {n} · P1: {n} · P2: {n} · P3: {n}

## Git

- Branch: {branch}
- Uncommitted: {n} files
- Recent:
  {last 5 commits}

## Health

| Gate   | Status |
| :----- | :----- |
| Ruff   | ✅/❌  |
| ESLint | ✅/❌  |
| TSC    | ✅/❌  |

## Velocity (Last 5 Sprints)

| Sprint           | Planned | Done | Sessions |
| :--------------- | :------ | :--- | :------- |
| {velocity table} |

## Recent Shipped

{last 3 entries from CHANGELOG.md}
```

### `/status brief` — One-Line Summary

```
Sprint {N}: {percent}% ({completed}/{total}) · {score}/100 readiness · {branch} · {n} uncommitted
```

### `/status health` — Gates Only

```markdown
## Health Check

| Gate              | Status |
| :---------------- | :----- |
| Ruff (Backend)    | ✅/❌  |
| ESLint (Frontend) | ✅/❌  |
| TSC (Frontend)    | ✅/❌  |

Verdict: {Healthy/Issues Found}
```

---

## Governance

**PROHIBITED:** Modifying any file · inventing numbers · reporting gates as ✅ without running them

**REQUIRED:** All data from source files · sprint progress from ROADMAP.md · P0 blockers surfaced

---

## Completion Criteria

- [ ] All relevant data sources loaded
- [ ] Sprint progress calculated from ROADMAP
- [ ] Output matches requested mode (full/brief/health)
- [ ] P0 blockers surfaced (if any exist)

## Related Resources

| Resource        | Path                         |
| :-------------- | :--------------------------- |
| ROADMAP         | `docs/ROADMAP.md`            |
| Session Context | `.agent/session-context.md`  |
| Session State   | `.agent/session-state.json`  |
| CHANGELOG       | `docs/CHANGELOG.md`          |
| Review Pipeline | `.agent/workflows/review.md` |
| Plan            | `.agent/workflows/plan.md`   |
