---
description: Code review workflow. Lint, type-check, test, security scan, and build verification.
---

# /review — Code Review Quality Gate

> **Trigger**: `/review` (full) · `/review lint` · `/review tests` · `/review security` · `/review build`
> **Lifecycle**: After implementation, before `/retrospective`

> [!CAUTION]
> Sequential gate pipeline — each step must pass before proceeding. Failed gates block merge. No overrides.

---

## 🔴 Critical Rules

1. **SEQUENTIAL** — each gate must pass before the next runs
2. **STOP ON FAILURE** — if a gate fails, stop immediately, show error + fix suggestion
3. **NO OVERRIDES** — failed gates block merge, no exceptions
4. **FULL-STACK** — both API (Python) and Web (TypeScript) are scanned
5. **DOCUMENT** — log results for audit trail

---

## Argument Parsing

| Command            | Gates Run                      |
| :----------------- | :----------------------------- |
| `/review`          | All gates (1-7)                |
| `/review lint`     | Gates 1-2 (Ruff + ESLint)      |
| `/review types`    | Gates 3-4 (MyPy + TSC)         |
| `/review tests`    | Gate 5 (Pytest)                |
| `/review security` | Gate 6 (npm audit + pip-audit) |
| `/review build`    | Gate 7 (Build)                 |

---

## Pipeline Gates

Execute gates IN ORDER. Stop at first failure.

### Gate 1: Lint — Backend

// turbo

```powershell
# Cwd: apps/api
& ".venv\Scripts\python.exe" -m ruff check app/ --quiet
```

### Gate 2: Lint — Frontend

// turbo

```powershell
# Cwd: apps/web
pnpm lint
```

### Gate 3: Type Check — Backend

// turbo

```powershell
# Cwd: apps/api
& ".venv\Scripts\python.exe" -m mypy app/
```

### Gate 4: Type Check — Frontend

// turbo

```powershell
# Cwd: apps/web
npx tsc --noEmit
```

### Gate 5: Tests — Backend

// turbo

```powershell
# Cwd: apps/api
& ".venv\Scripts\python.exe" -m pytest tests/ -q --tb=short
```

### Gate 6: Security Scan

// turbo

```powershell
# Cwd: apps/web
npm audit --audit-level=moderate

# Cwd: apps/api
& ".venv\Scripts\python.exe" -m pip_audit
```

### Gate 7: Build Verification

// turbo

```powershell
# Cwd: apps/web
pnpm build
```

---

## Output Format

### ✅ All Gates Passed

```markdown
## ✅ Review Complete

| Gate             | Scope | Status                | Duration |
| :--------------- | :---- | :-------------------- | :------- |
| Lint (Backend)   | api   | ✅ Pass               | {time}   |
| Lint (Frontend)  | web   | ✅ Pass               | {time}   |
| Types (Backend)  | api   | ✅ Pass               | {time}   |
| Types (Frontend) | web   | ✅ Pass               | {time}   |
| Tests            | api   | ✅ Pass ({n}/{n})     | {time}   |
| Security         | both  | ✅ No vulnerabilities | {time}   |
| Build            | web   | ✅ Pass ({n} routes)  | {time}   |

**Verdict**: Ready for commit.
```

### ❌ Gate Failed

```markdown
## ❌ Review Failed at Gate {N}

| Gate   | Status    |
| :----- | :-------- |
| {gate} | ❌ FAILED |

### Error Output

{error details}

### Recommended Fix

{fix steps}

Re-run: `/review` or `/review {gate}`
```

---

## Pre-Push Hook vs /review

| Aspect      | Pre-Push Hook (`ci-local.ps1`) | `/review`                        |
| :---------- | :----------------------------- | :------------------------------- |
| Trigger     | Automatic on `git push`        | Manual on-demand                 |
| Scope       | Subset (lint + types + build)  | Full 7-gate pipeline             |
| Interactive | No — blocks push silently      | Yes — shows output + suggestions |
| Use case    | Continuous quality enforcement | Pre-merge deep validation        |

> [!TIP]
> Enable automatic pre-push gating: `git config core.hooksPath .githooks`

---

## Governance

**PROHIBITED:** Skipping gates · overriding failures · merging without all gates passing · ignoring security scan results

**REQUIRED:** Run all 7 gates for merge-ready code · document results · fix failures before re-running · both API and Web scanned

---

## Completion Criteria

- [ ] All applicable gates executed in sequence
- [ ] Zero failures across all gates
- [ ] Results documented with pass/fail + duration
- [ ] Verdict rendered: "Ready for commit" or "Failed at Gate N"

## Related Resources

| Resource        | Path                                |
| :-------------- | :---------------------------------- |
| CI Local Script | `scripts/ci-local.ps1`              |
| Pre-Push Hook   | `.githooks/pre-push`                |
| Quality Gate    | `.agent/workflows/quality-gate.md`  |
| Retrospective   | `.agent/workflows/retrospective.md` |
| Plan            | `.agent/workflows/plan.md`          |
