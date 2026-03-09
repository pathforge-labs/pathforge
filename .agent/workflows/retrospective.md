---
description: PathForge Tier-1 Retrospective Quality Audit - Full product, architecture, and AI pipeline review against market standards
---

# /retrospective — Tier-1 Retrospective Quality Audit

> **Trigger**: `/retrospective` or `/tier1-audit`
> **Lifecycle**: After sprint/milestone completion — feeds next sprint's `/plan`

> [!CAUTION]
> Critical governance workflow. Do NOT defend previous decisions by default, minimize issues, or optimize for speed over correctness. Be critical, precise, honest — treat PathForge as competing with category leaders.

---

## When to Execute

- Major milestones (sprint completion, phase gates)
- Pre-launch reviews (alpha, beta, production)
- Quality regressions or concerns
- On-demand via `/retrospective`

---

## Audit Scope

Audit MUST automatically cover all applicable domains. Skip domains not yet implemented.

| Domain                 | What to Audit                                           |
| :--------------------- | :------------------------------------------------------ |
| **Semantic Analysis**  | Job parsing, NLP quality, entity extraction             |
| **LLM Pipeline**       | CV/cover letter optimization, prompts, token efficiency |
| **Skill Gap Scoring**  | Algorithm fairness, accuracy, explainability            |
| **Browser Automation** | Human-in-the-loop, rate limiting, ToS compliance        |
| **Application Funnel** | Measurable stages, conversion tracking, feedback        |
| **Market Insights**    | Data freshness, accuracy, geographic relevance          |
| **Architecture**       | Backend, frontend, infra, database, AI integration      |
| **Auth & Onboarding**  | Registration, login, profile, data import               |
| **Public Surface**     | Landing page, messaging, positioning, SEO               |
| **Security & Privacy** | Data handling, encryption, GDPR, data sovereignty       |
| **AI Ethics & Bias**   | Scoring fairness, demographic bias, transparency        |
| **Testing**            | Coverage, strategy, regression prevention               |

> [!IMPORTANT]
> Nothing is assumed correct. Every completed item is subject to re-evaluation.

---

## Steps

Execute IN ORDER. Do not skip any step.

### Step 1: Inventory Collection

// turbo

Load and catalog: project docs, task tracking, git log (main), ADRs, feature specs, AI pipeline configs. Produce a **Completed Task & System Inventory**.

### Step 2: Market Benchmark Analysis

// turbo

For each feature, evaluate against market leaders (LinkedIn, Indeed, Glassdoor, Stepstone, Hired) and AI-native competitors (Jobscan, Rezi, Teal, Huntr, LazyApply):

| Feature | PathForge  | Market Leader | Gap?     | Notes    |
| :------ | :--------- | :------------ | :------- | :------- |
| [name]  | [approach] | [best impl.]  | ✅/⚠️/❌ | [detail] |

### Step 3: Outdated Pattern Detection

Evaluate each item:

- Legacy UX, architecture, or AI pipeline assumptions?
- Deprecated libraries, patterns, or anti-patterns?
- Reflects 2024-2026 best practices or older thinking?

| Area   | Current  | Issue          | Modern Alternative |
| :----- | :------- | :------------- | :----------------- |
| [area] | [exists] | [why outdated] | [replacement]      |

### Step 4: Tier-1 Quality Validation

For each system: Would it pass review at Google/Meta/Apple? Senior-level or merely functional? Shortcuts, missing edge cases? Code quality meet strict TypeScript/testing standards? AI pipelines reproducible and benchmarked?

### Step 5: Ethics, Bias & Automation Safety

- AI scoring bias (demographic, linguistic)?
- Automated actions transparent and explainable?
- GDPR compliance and data sovereignty?
- Automation safeguards effective (human-in-the-loop, rate limiting, opt-out)?
- Browser automation ToS compliant?

### Step 6: Differentiation Alignment

Check each feature against PathForge values:

- Precision > Volume philosophy?
- Measurable, transparent funnels?
- Human-in-the-loop control?
- Ethical automation (anti-spam, ToS)?
- Explainable AI scoring?
- Data sovereignty preserved?

### Step 7: Classification & Reporting

| Classification         | Meaning                             | Action             |
| :--------------------- | :---------------------------------- | :----------------- |
| ✅ Tier-1 Compliant    | Meets/exceeds standards + values    | None               |
| ⚠️ Partially Compliant | Functional but below Tier-1         | Refinement plan    |
| ❌ Non-Compliant       | Below market or violates principles | Revision — blocker |

---

## Output Template

```markdown
# PathForge Tier-1 Retrospective Audit Report

> Date: [date] · Sprint: [N] · Auditor: Antigravity AI Kit

## 1. Executive Summary

## 2. System Inventory

## 3. Compliance Classification (✅/⚠️/❌ per area)

## 4. Gaps & Risks

## 5. Outdated Implementations

## 6. Revision Recommendations (change + justification + impact)

## 7. Priority Matrix

| Priority    | Issue | Impact | Effort |
| :---------- | :---- | :----- | :----- |
| 🔴 Critical | ...   | ...    | ...    |
| 🟠 High     | ...   | ...    | ...    |
| 🟢 Optional | ...   | ...    | ...    |

## 8. Conclusion & Next Steps
```

---

## Revision Rules

1. Prefer structural improvements over cosmetic fixes
2. Avoid incremental patching when foundations are weak
3. Provide concrete examples — not vague suggestions
4. Reference market data to justify every recommendation

---

## Governance

**PROHIBITED:** Defending past decisions by default · minimizing issues · optimizing speed over correctness · marking ✅ without evidence · skipping domains

**REQUIRED:** PhD-level rigor · market-grade bar · revisions for all non-compliant areas · actionable recommendations · competitor/best-practice citations

---

## Completion Criteria

- [ ] All applicable domains inventoried and analyzed
- [ ] Every item classified (✅/⚠️/❌)
- [ ] All gaps documented with evidence
- [ ] Revision path for every non-compliant area
- [ ] Priority Matrix populated
- [ ] Audit report saved as artifact
- [ ] Findings presented to Product Owner via `notify_user`

> [!NOTE]
> If no gaps found, explicitly state WHY with evidence from benchmarks and quality metrics.

## Related Resources

| Resource        | Path                               |
| :-------------- | :--------------------------------- |
| Quality Gate    | `.agent/workflows/quality-gate.md` |
| Plan            | `.agent/workflows/plan.md`         |
| Review          | `.agent/workflows/review.md`       |
| Product Context | `.agent/product.md`                |
| ADR Directory   | `.agent/decisions/`                |
