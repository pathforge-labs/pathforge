---
description: Systematic debugging workflow. Activates DEBUG mode for problem investigation.
---

# /debug - Systematic Problem Investigation

$ARGUMENTS

---

## Purpose

Activates DEBUG mode for systematic investigation of issues, errors, or unexpected behavior.
Uses the `debugging-strategies` skill (4-phase methodology with Iron Law enforcement).

---

## Behavior

### Phase 1: Root Cause Investigation

1. **Read error messages** — full stack trace, error codes, line numbers
2. **Reproduce** — exact steps, consistent trigger, environment details
3. **Check recent changes** — `git log`, `git diff`, new deps or config
4. **Multi-component trace** — add diagnostic logging at each layer boundary (API → Service → DB)

> ⚠️ **Iron Law**: NO fixes proposed until Phase 1 is complete.

### Phase 2: Pattern Analysis

5. **Find working examples** — similar working code in codebase
6. **Compare** — identify every difference between working and broken
7. **Understand dependencies** — config, environment, assumptions

### Phase 3: Hypothesis & Testing

8. **Form single hypothesis** — "I think X because Y"
9. **Test minimally** — smallest possible change, one variable at a time
10. **Verify** — worked → Phase 4, didn't → new hypothesis (don't stack fixes)

### Phase 4: Implementation

11. **Create failing test** — automated regression test before fixing
12. **Implement single fix** — address root cause, one change only
13. **Verify fix** — failing test passes, full suite green, original issue resolved

---

## Output Format

```markdown
## 🔍 Debug: [Issue]

### Phase 1: Root Cause Investigation

**Symptom**: [What's happening]
**Error**: `[error message]`
**File**: `[filepath:line]`
**Recent changes**: [git log/diff findings]
**Layer trace**: [which boundary fails]

### Phase 2: Pattern Analysis

**Working reference**: [similar working code]
**Key differences**: [what's different]

### Phase 3: Hypothesis

🎯 **Hypothesis**: "I think [X] is the root cause because [Y]"
**Test**: [minimal change to verify]
**Result**: ✅ Confirmed / ❌ Refuted → [new hypothesis]

### Phase 4: Fix

**Root cause**: [explanation]
**Regression test**: [test name + assertion]
**Fix**: [code change]
**Verification**: [test suite results]
**Prevention**: 🛡️ [defense-in-depth measures]
```

---

## Escalation Protocol

If **3+ fixes** have failed:

1. **STOP** — don't attempt Fix #4
2. **Question architecture** — is the pattern fundamentally sound?
3. **Discuss with user** — present evidence from all 3 attempts
4. **Consider refactor** — architecture change vs. symptom patching

---

## Examples

```
/debug login not working
/debug API returns 500
/debug tests failing after migration
/debug CI build broken
/debug career DNA generation timeout
```

---

## Key Principles

- **Root cause first** — no fixes without investigation
- **One hypothesis at a time** — don't stack changes
- **Test before fixing** — create failing test first
- **Fix at source** — use root-cause-tracing, not symptom patching
- **Defend in depth** — add validation at multiple layers after fix
