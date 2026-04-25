# Salary Intelligence Engine™ — Quality Gate Research Summary

> **Sprint**: 11 · **Phase**: B (Career Intelligence)
> **Research Date**: 2026-02-20
> **Protocol**: `/quality-gate` Pre-Task Research & Validation

---

## Step 1: Market Research (6 Competitors)

| Platform            | What They Do                       | Personalized?           | Data Source                 | Limitation                        |
| :------------------ | :--------------------------------- | :---------------------- | :-------------------------- | :-------------------------------- |
| **Glassdoor**       | Average salary per role + location | ❌ Aggregate            | User-reported               | No skill-level granularity        |
| **Levels.fyi**      | Company-specific compensation (TC) | ❌ Company-level        | Self-reported tech salaries | Tech-only, no individual modeling |
| **Payscale**        | Parametric Bayesian salary ranges  | ⚠️ Partial (survey)     | Employer + employee surveys | Requires manual questionnaire     |
| **Pave / Ravio**    | Real-time comp benchmarking        | ❌ Employer-focused     | Payroll integrations        | Enterprise B2B, not consumer      |
| **SalaryCube**      | Continuous market data streams     | ❌ Aggregate            | Job posting analysis        | No career trajectory over time    |
| **LinkedIn Salary** | Role-based salary ranges           | ⚠️ Partial (role + YoE) | Member-reported             | No skill impact modeling          |

---

## Step 2: Comparative Analysis

| Dimension          | Market Standard                | PathForge Approach                                                  |
| :----------------- | :----------------------------- | :------------------------------------------------------------------ |
| **Input**          | Manual survey / role selection | Automatic from Career DNA                                           |
| **Granularity**    | Role × Location × Seniority    | Role × Location × Seniority × **Individual skills** × Market demand |
| **Skill Impact**   | None — skills ignored          | Each skill has a quantified salary premium/penalty                  |
| **Time Dimension** | Snapshot only                  | Historical trajectory + 6/12-month projection                       |
| **What-If**        | None                           | "What would adding skill X do to my salary?"                        |
| **Confidence**     | Opaque                         | Transparent confidence interval with data point count               |
| **Integration**    | Standalone                     | Cross-referenced with Skill Decay, Career DNA, Threat Radar         |

---

## Step 3: Gap Detection

- ✅ PathForge **exceeds** market on personalization (Career DNA integration)
- ✅ PathForge **exceeds** market on skill→salary impact modeling (unique feature)
- ✅ PathForge **exceeds** market on time-series trajectory (no competitor offers this)
- ⚠️ Market data accuracy depends on LLM intelligence + aggregator APIs — need robust fallbacks

---

## Step 4: Enhancement Strategy

| Dimension        | How PathForge Improves                                                             |
| :--------------- | :--------------------------------------------------------------------------------- |
| **Transparency** | Confidence interval + data point count + factor breakdown                          |
| **User Control** | Users can override location/seniority and run what-if scenarios                    |
| **Accuracy**     | Multi-factor model: base × skills × experience × market conditions                 |
| **Ethics**       | No salary data collection from users — LLM-estimated from Career DNA + market data |
| **Integration**  | Feeds into Interview Intelligence (Sprint 14) negotiation scripts                  |

---

## Step 5: Ethics & Bias Assessment

| Risk                      | Severity | Mitigation                                                                        |
| :------------------------ | :------- | :-------------------------------------------------------------------------------- |
| **Gender/ethnicity bias** | High     | Salary estimates based on skills + market data only — no demographic inputs       |
| **LLM hallucination**     | Medium   | Output validation with range clamps, confidence scoring, fallback static ranges   |
| **Salary overestimation** | Medium   | Conservative confidence intervals, "data points" transparency                     |
| **Privacy**               | Low      | No salary collection — all estimates derived from public market data + Career DNA |
| **GDPR**                  | Low      | Estimates stored per career_dna_id with CASCADE delete                            |

---

## Architecture Decision: Personalized Salary Formula

```
PersonalizedSalary = BaseSalary(role, location, seniority)
                   × SkillPremiumFactor(rare_skills, in_demand_skills)
                   × ExperienceMultiplier(years, relevance)
                   × MarketConditionAdjustment(supply_demand_ratio)
                   ± ConfidenceInterval(data_points, recency)
```

This multi-factor approach ensures that PathForge's salary intelligence is **personalized** to each user's unique career profile — not an aggregate number from a database lookup.

---

_Research conducted following PathForge `/quality-gate` protocol (Steps 1–5 mandatory)._
