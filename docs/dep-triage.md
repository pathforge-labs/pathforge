# PathForge — Dependency Deprecation Triage (N-7)

**Date**: 2026-04-23  
**Sprint**: 43  
**Author**: Senior Staff Engineer (PathForge quality-playbook authority)  
**Status**: Complete — all findings triaged; `package.json` unblocked for future touches

---

## Purpose

This document records the formal triage decision for every deprecated package found in
the `pnpm-lock.yaml` transitive tree. It is the single reference engineers should consult
before opening a `package.json` change, ensuring no finding is silently ignored.

Re-evaluation cadence: each sprint boundary, or whenever a major direct dependency is
upgraded (Next.js, Expo, Babel, ESLint).

---

## Triage Key

| Decision | Meaning |
|:--|:--|
| **UPGRADE** | Fixed now — override added or direct dep bumped |
| **PARK** | Defer — blocked on upstream; re-evaluate on next major upgrade of the parent |
| **IGNORE** | Intentional — deprecated but no replacement; no security/runtime impact |

---

## Findings

### 1. `@babel/plugin-transform-class-properties`

| Field | Value |
|:--|:--|
| **Source** | Transitive via `eslint-config-next` → `@next/eslint-plugin-next` → `@babel/*` |
| **Deprecation reason** | Proposal landed in ES2022 standard; plugin merged into `@babel/preset-env` |
| **Runtime impact** | None — dev-only ESLint tooling path |
| **Security impact** | None |
| **Decision** | **PARK** |
| **Rationale** | Direct parent is `eslint-config-next` which is pinned to the Next.js release train. Upgrading independently risks Babel version conflicts with Next.js internals. The plugin is dev-only and produces no warning at runtime. Fix by upgrading to the next major `eslint-config-next` when available. |
| **Re-evaluate** | On next `eslint-config-next` major |

---

### 2. `@babel/plugin-transform-nullish-coalescing-operator`

| Field | Value |
|:--|:--|
| **Source** | Same as above (`eslint-config-next` transitive tree) |
| **Deprecation reason** | `??` operator landed in ES2020; merged into `@babel/preset-env` |
| **Runtime impact** | None — dev-only |
| **Security impact** | None |
| **Decision** | **PARK** |
| **Rationale** | Identical to `class-properties` entry above. Parent upgrade resolves both. |
| **Re-evaluate** | On next `eslint-config-next` major |

---

### 3. `@babel/plugin-transform-optional-chaining`

| Field | Value |
|:--|:--|
| **Source** | Same as above |
| **Deprecation reason** | `?.` operator landed in ES2020; merged into `@babel/preset-env` |
| **Runtime impact** | None — dev-only |
| **Security impact** | None |
| **Decision** | **PARK** |
| **Rationale** | Same as above. All three Babel transform deprecations are resolved by a single `eslint-config-next` upgrade. |
| **Re-evaluate** | On next `eslint-config-next` major |

---

### 4. `memorystream`

| Field | Value |
|:--|:--|
| **Source** | Transitive via test tooling (likely `jest-expo` or `msw`) |
| **Deprecation reason** | Package archived; documented memory leak with large streams |
| **Runtime impact** | None — test-only path; small payloads in unit tests do not trigger the leak |
| **Security impact** | None |
| **Decision** | **PARK** |
| **Rationale** | No maintained fork or drop-in replacement exists. The memory leak only manifests under sustained large-stream workloads, which do not occur in unit test contexts. Parent package (`jest-expo`) must drop or replace it upstream. |
| **Re-evaluate** | On next `jest-expo` major bump |

---

### 5. `rimraf < 4`

| Field | Value |
|:--|:--|
| **Source** | Transitive via multiple build tools (glob patterns used by older tool versions) |
| **Deprecation reason** | `rimraf@4` dropped legacy glob support; v3 marked deprecated |
| **Runtime impact** | None — build/clean scripts only |
| **Security impact** | None |
| **Decision** | **PARK** |
| **Rationale** | `rimraf@4` has a breaking API change (glob option removed). Forcing an override to `>=4` would break any transitive consumer that passes a glob pattern to `rimraf()`. Safe upgrade requires each parent to migrate their call site first. No CVE is associated with this deprecation. |
| **Re-evaluate** | On next major tool upgrade (webpack, Next.js bundler internals) |

---

## Summary

All five deprecated packages are **transitive** (not direct dependencies) and are **dev/build-only**
(no production runtime impact). None carry a CVE. None can be safely force-upgraded via pnpm
`overrides` without risking API breakage in parent tooling.

**Action**: PARK all. No `package.json` changes required. This document itself is the deliverable —
future `package.json` touches are unblocked because every deprecation warning now has an explicit,
justified triage decision rather than an unknown state.

---

## Re-evaluation Triggers

| Trigger | Action |
|:--|:--|
| `eslint-config-next` major release | Re-check Babel transform plugins — likely resolved |
| `jest-expo` major bump | Re-check `memorystream` — may be dropped |
| Next.js bundler major (webpack → turbopack full) | Re-check all Babel transitives |
| Any new `pnpm audit --deprecations` output | Add new findings to this doc before merging the PR that introduced them |
