---
name: debugging-strategies
description: Systematic debugging approaches for complex problems
triggers: [context, debug, error, bug, fix, investigate, troubleshoot, broken]
---

# Systematic Debugging — Trust-Grade Methodology

> **Purpose**: Enforce root-cause-first debugging discipline. Eliminate random fix attempts, reduce thrashing, and produce durable solutions.
>
> **Origin**: Adapted from [obra/superpowers/systematic-debugging](https://skills.sh/obra/superpowers/systematic-debugging) for PathForge conventions.

---

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you **cannot** propose fixes.
Symptom fixes are failure. Quick patches mask underlying issues.

---

## When to Use

Use for **ANY** technical issue:

- Test failures
- Bugs in production or development
- Unexpected behavior
- Performance problems
- Build or CI failures
- Integration issues (API ↔ Service ↔ DB)

Use **ESPECIALLY** when:

- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip** when:

- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (systematic is faster than thrashing)
- Stakeholder wants it fixed NOW (discipline prevents rework)

---

## The Four Phases

You **MUST** complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

BEFORE attempting ANY fix:

#### 1. Read Error Messages Carefully

- Don't skip past errors or warnings — they often contain the exact solution
- Read stack traces **completely**
- Note line numbers, file paths, error codes
- In Python: read the full traceback, including chained exceptions (`__cause__`)
- In TypeScript: check both the error message and the component stack

#### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, **don't guess**

#### 3. Check Recent Changes

- What changed that could cause this?
- `git log --oneline -10` and `git diff HEAD~5..HEAD -- <path>`
- New dependencies, config changes, environment differences
- Review recent Alembic migrations if DB-related

#### 4. Gather Evidence in Multi-Component Systems

When the system has multiple components (CI → build → test, API → Service → DB → LLM):

**BEFORE proposing fixes**, add diagnostic instrumentation:

```
For EACH component boundary:
  → Log what data enters the component
  → Log what data exits the component
  → Verify environment/config propagation
  → Check state at each layer

Run once to gather evidence showing WHERE it breaks
THEN analyze evidence to identify failing component
THEN investigate that specific component
```

**PathForge example** (API → Service → DB):

```python
# Layer 1: API endpoint
logger.debug(f"[API] Request received: user_id={current_user.id}, payload={request_data}")

# Layer 2: Service method
logger.debug(f"[Service] Input: {input_data}, DB session active: {session.is_active}")

# Layer 3: DB query
logger.debug(f"[DB] Query: {str(query)}, params: {query.parameters}")

# Layer 4: Response
logger.debug(f"[API] Response: status={response.status_code}, body_size={len(response.body)}")
```

This reveals: which layer fails (API → Service ✓, Service → DB ✗).

#### 5. Trace Data Flow

When error is deep in the call stack:

- See [root-cause-tracing.md](./root-cause-tracing.md) for the complete backward tracing technique
- Quick version: Where does the bad value originate? → What called this with the bad value? → Keep tracing up until you find the source → Fix at source, not at symptom

---

### Phase 2: Pattern Analysis

Find the pattern before fixing:

#### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?
- Example: if a new service method fails, compare with an adjacent working method in the same service

#### 2. Compare Against References

- If implementing a pattern, read the reference implementation **COMPLETELY**
- Don't skim — read every line
- Understand the pattern fully before applying

#### 3. Identify Differences

- What's different between working and broken?
- List **every** difference, however small
- Don't assume "that can't matter"

#### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

### Phase 3: Hypothesis & Testing

Apply the scientific method:

#### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down (in the debug output format)
- Be specific, not vague

#### 2. Test Minimally

- Make the **SMALLEST** possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

#### 3. Verify Before Continuing

- Did it work? **Yes** → Phase 4
- Didn't work? Form a **NEW** hypothesis
- **DON'T** add more fixes on top

#### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help or context
- Research more before guessing

---

### Phase 4: Implementation

Fix the root cause, not the symptom:

#### 1. Create a Failing Test Case

- Simplest possible reproduction
- Automated test if possible (pytest / Vitest)
- One-off test script if no framework applies
- MUST have before fixing

#### 2. Implement a Single Fix

- Address the root cause identified in Phase 1–3
- **ONE** change at a time
- No "while I'm here" improvements
- No bundled refactoring

#### 3. Verify the Fix

- Does the failing test pass now?
- Are all other tests still passing? (`pytest` / `pnpm test`)
- Is the original issue actually resolved?

#### 4. If the Fix Doesn't Work

- **STOP**
- Count: How many fixes have you tried?
- If **< 3**: Return to Phase 1, re-analyze with new information
- If **≥ 3**: STOP and question the architecture (step 5 below)
- **DON'T** attempt Fix #4 without an architectural discussion

#### 5. If 3+ Fixes Failed: Question Architecture

Patterns indicating an architectural problem:

- Each fix reveals new shared state / coupling / problem in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP** and question fundamentals:

- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor architecture vs. continue fixing symptoms?

**Discuss with the user** before attempting more fixes.
This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems:" (listing fixes without investigation)
- Proposing solutions before tracing data flow
- "One more fix attempt" (when already tried 2+)
- Each fix reveals a new problem in a different place

**ALL** of these mean: **STOP. Return to Phase 1.**

If 3+ fixes failed: Question the architecture (see Phase 4.5).

---

## User Signals You're Off Track

Watch for these redirections from the user:

| Signal                      | Meaning                                      |
| :-------------------------- | :------------------------------------------- |
| "Is that not happening?"    | You assumed without verifying                |
| "Will it show us...?"       | You should have added evidence gathering     |
| "Stop guessing"             | You're proposing fixes without understanding |
| "Ultrathink this"           | Question fundamentals, not just symptoms     |
| "We're stuck?" (frustrated) | Your approach isn't working                  |

When you see these: **STOP. Return to Phase 1.**

---

## Supporting Techniques

- [root-cause-tracing.md](./root-cause-tracing.md) — Trace bugs backward through call stack to find the original trigger
- [defense-in-depth.md](./defense-in-depth.md) — Add validation at multiple layers after finding root cause

---

## Real-World Impact

From debugging sessions (obra/superpowers data):

| Approach     | Time to Fix | First-Time Fix Rate | New Bugs Introduced |
| :----------- | :---------- | :------------------ | :------------------ |
| Systematic   | 15–30 min   | ~95%                | Near zero           |
| Random fixes | 2–3 hours   | ~40%                | Common              |

---

## Quick Reference

| Symptom                       | Likely Cause                |
| :---------------------------- | :-------------------------- |
| `undefined is not an object`  | Null reference              |
| `Maximum call stack exceeded` | Infinite recursion          |
| `Cannot read property`        | Missing null check          |
| `CORS error`                  | Backend config / middleware |
| `401 Unauthorized`            | Token expired or missing    |
| `422 Unprocessable Entity`    | Pydantic validation failure |
| `500 Internal Server Error`   | Unhandled exception         |
| `IntegrityError`              | DB constraint violation     |
| `ModuleNotFoundError`         | Import path / venv issue    |
| `Hydration mismatch`          | SSR/CSR content difference  |
