# Security Policy

## Supported Versions

| Version | Supported          |
| :------ | :----------------- |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously at PathForge. If you discover a security vulnerability, please report it responsibly.

### How to Report

- **Email**: [security@pathforge.eu](mailto:security@pathforge.eu)
- **Response Time**: We aim to acknowledge reports within 48 hours
- **Resolution**: Critical vulnerabilities are prioritized and patched within 7 days

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### What to Expect

1. **Acknowledgment** within 48 hours
2. **Assessment** and severity classification within 5 business days
3. **Fix and disclosure** coordinated with the reporter

### Scope

- PathForge API (`api.pathforge.eu`)
- PathForge Web (`pathforge.eu`)
- GitHub repository and CI/CD pipelines

### Out of Scope

- Social engineering attacks
- Denial of service attacks
- Issues in third-party dependencies (report upstream)

## Security Practices

- OWASP-compliant security headers on all API responses
- HSTS enforcement in production
- JWT token blacklisting on logout
- Rate limiting on sensitive endpoints
- Input sanitization with OWASP LLM01 prompt injection defense
- Redis-backed session management
- Environment-based secret management (never hardcoded)

## Security Contact

- **Email**: security@pathforge.eu
- **security.txt**: [https://api.pathforge.eu/.well-known/security.txt](https://api.pathforge.eu/.well-known/security.txt)

---

## Ignored CVEs (justification register)

The `auditConfig.ignoreCves` array in [package.json](package.json) excludes
the following advisories from the blocking `pnpm audit` CI step. Each
entry below records **what**, **why**, and **when to re-evaluate**. Any
new addition to the ignore list MUST include a matching row here in the
same PR (enforced by code review; a future improvement is a pre-commit
hook).

> **Discoverability**: engineers hitting a `CVE-20XX-…` in `package.json`
> can find the rationale by grepping the CVE ID in the repo — every
> entry is enumerated here. We intentionally do NOT put a `"//"`
> comment-key pointer in `package.json` because any change to that file
> triggers the `web` CI path filter, which runs `pnpm audit` and can
> fail on pre-existing CVEs unrelated to a docs-hygiene PR.

Re-evaluation runs every sprint boundary. An entry that is still valid
keeps its row; an entry whose upstream fix has landed is removed from
the ignore list AND struck through here with the removal commit.

| CVE | Severity | Package | Dev / Prod | Why ignored | Re-evaluate by | Added |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CVE-2025-69873 | Moderate | `ajv` 6.x (transitive via ESLint → `@eslint/eslintrc`) | **Dev-only** | ESLint 8.x pins ajv@6 for the `missingRefs` API; upstream ajv 6.14.0 removed that API and breaks ESLint. ajv is never loaded at runtime (no FastAPI/Next.js path resolves it). Classified as an ESLint-tooling false positive for our deployment model. | 2026-Q3 — ESLint 9.x removes the ajv dependency entirely. If ESLint 9 is adopted before then, drop this entry. | 2026-02-19 (commit `0af9795`) |
| CVE-2025-09073 | Moderate (CVSS 5.5) | `ajv` 6.12.6 ReDoS via `$data` option (transitive via ESLint → `@eslint/eslintrc`) | **Dev-only** | Same dependency path as above. We do not use the `$data` schema option anywhere in our ESLint config, so the ReDoS path is unreachable in our toolchain. Upgrade to ajv 6.14.0 would require fork-patching ESLint's `missingRefs` usage — disproportionate for a dev-time tool that processes trusted input (our own source code). | 2026-Q3 — same condition as CVE-2025-69873. | 2026-02-20 (commit `4c5dd47`) |
| CVE-2026-33671 | High | `picomatch@4.0.3` (transitive via `apps/mobile>expo>@expo/cli`) | **Dev-only / Mobile toolchain** | `@expo/cli` pins `picomatch` to the exact version `4.0.3` in its manifest. The pnpm override mechanism cannot force-bump exact-version pins in transitive sub-packages. `picomatch` is used inside the Expo CLI for file-pattern matching during development builds — it is never bundled into the production API or web app. The `pnpm audit --prod` flag already excludes devDependencies; this finding surfaces because the workspace root scan includes the mobile workspace. Impact is limited to local/CI build tooling. | When `@expo/cli` upgrades its internal `picomatch` dependency to `>=4.0.4`, remove this entry and the matching override. Target: Expo SDK 53+ release cycle. | 2026-04-23 (commit `5144bda`) |
| CVE-2026-33672 | Moderate | `picomatch@4.0.3` (transitive via `apps/mobile>expo>@expo/cli`) | **Dev-only / Mobile toolchain** | Same package and dependency chain as CVE-2026-33671. Two separate advisories (GHSA-c2c7-rcm5-vvqj, GHSA-3v7f-55p6-f55p) reference the same `picomatch@4.0.3` exact-pin from `@expo/cli`. Resolution and re-evaluation conditions are identical. | Same as CVE-2026-33671. | 2026-04-23 (commit `5144bda`) |
| GHSA-q3j6-qgpj-74h6 | High | `fast-uri` <=3.1.0 path-traversal (transitive via `apps/mobile>expo-router>schema-utils>ajv>fast-uri`) | **Dev-only / Mobile toolchain** | `fast-uri` ships exclusively under the mobile workspace's Expo Router schema-validation chain. The mobile app is **not currently deployed** — only the API (Railway) and web (Vercel) are in production, and neither resolves `fast-uri`. The advisory requires attacker-controlled URI input passed to `fast-uri.parse()`; even if the mobile app deploys later, Expo Router uses `fast-uri` only for parsing its own static route schemas, not user input. Same reachability profile as the existing picomatch ignores (CVE-2026-33671/33672) which are also Expo-toolchain transitives. | When `expo-router` (or its `schema-utils>ajv` parent) upgrades to a `fast-uri >=3.1.2` resolution, remove this entry. Target: next Expo SDK minor. | 2026-05-10 |
| GHSA-v39h-62p7-jpjc | High | `fast-uri` <=3.1.1 host-confusion (same dep path as GHSA-q3j6-qgpj-74h6) | **Dev-only / Mobile toolchain** | Same dependency path and reachability profile. The "host confusion" attack requires an adversary-supplied URI parsed for hostname trust decisions; Expo Router never routes user input through `fast-uri` for such decisions. | Same conditions as GHSA-q3j6-qgpj-74h6. | 2026-05-10 |
| GHSA-fv7c-fp4j-7gwp | High | `@babel/plugin-transform-modules-systemjs` 7.12.0–7.29.3 (transitive via `apps/mobile>expo>babel-preset-expo>@react-native/babel-preset>@react-native/babel-plugin-codegen>@react-native/codegen>@babel/preset-env>@babel/plugin-transform-modules-systemjs`) | **Dev-only / Mobile toolchain** | Pure mobile-toolchain transitive — surfaces from React Native's Babel preset chain. The web app builds with Next.js + SWC (not Babel) and contains zero references to this plugin in its bundle. The vulnerability is in generated SystemJS runtime code; React Native does not emit SystemJS modules either, the plugin is part of the dep graph but never invoked. | When `@react-native/babel-preset` upgrades its `@babel/preset-env` (which then resolves `@babel/plugin-transform-modules-systemjs >=7.29.4`), remove this entry. Target: next React Native / Expo SDK release. | 2026-05-10 |

**Policy**:
- Ignoring a CVE is a risk-acceptance decision, not a default. Every
  entry here is owned by `security@pathforge.eu` and carries a clock.
- An ignore that would hide a **production**-runtime vulnerability is
  forbidden — only dev-only paths qualify.
- A re-evaluation date beyond 6 months requires an ADR explaining why.
