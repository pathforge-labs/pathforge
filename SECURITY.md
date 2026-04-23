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

Re-evaluation runs every sprint boundary. An entry that is still valid
keeps its row; an entry whose upstream fix has landed is removed from
the ignore list AND struck through here with the removal commit.

| CVE | Severity | Package | Dev / Prod | Why ignored | Re-evaluate by | Added |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CVE-2025-69873 | Moderate | `ajv` 6.x (transitive via ESLint → `@eslint/eslintrc`) | **Dev-only** | ESLint 8.x pins ajv@6 for the `missingRefs` API; upstream ajv 6.14.0 removed that API and breaks ESLint. ajv is never loaded at runtime (no FastAPI/Next.js path resolves it). Classified as an ESLint-tooling false positive for our deployment model. | 2026-Q3 — ESLint 9.x removes the ajv dependency entirely. If ESLint 9 is adopted before then, drop this entry. | 2026-02-19 (commit `0af9795`) |
| CVE-2025-09073 | Moderate (CVSS 5.5) | `ajv` 6.12.6 ReDoS via `$data` option (transitive via ESLint → `@eslint/eslintrc`) | **Dev-only** | Same dependency path as above. We do not use the `$data` schema option anywhere in our ESLint config, so the ReDoS path is unreachable in our toolchain. Upgrade to ajv 6.14.0 would require fork-patching ESLint's `missingRefs` usage — disproportionate for a dev-time tool that processes trusted input (our own source code). | 2026-Q3 — same condition as CVE-2025-69873. | 2026-02-20 (commit `4c5dd47`) |

**Policy**:
- Ignoring a CVE is a risk-acceptance decision, not a default. Every
  entry here is owned by `security@pathforge.eu` and carries a clock.
- An ignore that would hide a **production**-runtime vulnerability is
  forbidden — only dev-only paths qualify.
- A re-evaluation date beyond 6 months requires an ADR explaining why.
