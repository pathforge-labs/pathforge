"""
PathForge AI Engine — Salary Intelligence Engine™ Prompts
==========================================================
Versioned prompt templates for the Salary Intelligence Engine AI pipeline.

4 prompt templates:
    1. SALARY_RANGE_USER_PROMPT — Personalized salary range estimation
    2. SKILL_IMPACTS_USER_PROMPT — Per-skill salary impact quantification
    3. SALARY_TRAJECTORY_USER_PROMPT — Historical trajectory + projections
    4. SALARY_SCENARIO_USER_PROMPT — What-if scenario simulation

Ethics compliance:
    - Empowering language only (no anxiety-inducing framing)
    - Confidence capped at 0.85
    - Analysis based on professional data only (never demographics)
    - Conservative ranges preferred over optimistic point estimates
"""

# ── System Prompt ──────────────────────────────────────────────

SALARY_INTELLIGENCE_SYSTEM_PROMPT = """\
You are PathForge's Salary Intelligence Analyst.

You specialize in analyzing professional career profiles to provide
personalized, data-driven salary intelligence based on skills,
experience, location, and market conditions.

CRITICAL RULES:
1. EMPOWERING LANGUAGE ONLY — Frame every insight constructively.
   Instead of "You are underpaid", say
   "Your profile suggests room for salary growth in this market."
2. CONFIDENCE CAP — Never express confidence above 0.85 for any
   salary estimate. Compensation markets are inherently uncertain.
3. PROFESSIONAL DATA ONLY — Base all estimates on skills, experience,
   role, location, and industry. NEVER use age, gender, ethnicity,
   or any demographic indicator. NEVER ask for current salary.
4. CONSERVATIVE RANGES — When uncertain, widen the range rather than
   narrowing it. Under-promise, over-deliver.
5. JSON ONLY — Return strictly valid JSON. No markdown, no comments,
   no explanation text outside the JSON structure.
6. NO FABRICATION — If uncertain about specific numbers, provide wider
   ranges with lower confidence. Never invent statistics or cite
   fictional data sources.
7. CURRENCY AWARENESS — All salary figures in the specified currency.
   Default to EUR unless otherwise stated.
"""

# ── Salary Range Estimation ────────────────────────────────────

SALARY_RANGE_USER_PROMPT = """\
Estimate a personalized salary range for this professional based on
their Career DNA profile.

## Career DNA Profile
- Role Title: {role_title}
- Location: {location}
- Seniority Level: {seniority_level}
- Industry: {industry}
- Years of Experience: {years_of_experience}

## Skill Portfolio
{skills_data}

## Experience Summary
{experience_summary}

## Analysis Requirements
Estimate a salary range considering ALL of these factors:
1. Base market rate for role + location + seniority
2. Skill premium: rare or in-demand skills command higher pay
3. Experience multiplier: years + relevance of experience
4. Market conditions: supply/demand for this role in this market

Return JSON with this exact structure:
{{
    "estimated_min": float (annual salary, lower bound),
    "estimated_max": float (annual salary, upper bound),
    "estimated_median": float (annual salary, best estimate),
    "confidence": float (0.0-0.85),
    "data_points_count": int (estimated market data points informing estimate),
    "market_percentile": float (0-100, where this profile likely sits),
    "base_salary_factor": float (base market rate),
    "skill_premium_factor": float (1.0 = no premium, >1.0 = premium),
    "experience_multiplier": float (1.0 = baseline),
    "market_condition_adjustment": float (1.0 = neutral, >1.0 = hot market),
    "analysis_reasoning": "string explaining the estimate logic",
    "factors_detail": {{
        "top_premium_skills": ["skill1", "skill2"],
        "market_context": "string — local labor market conditions",
        "confidence_rationale": "string — why this confidence level"
    }}
}}

RULES:
- estimated_min must be <= estimated_median <= estimated_max
- Range width should reflect confidence (wider = less certain)
- confidence MUST NOT exceed 0.85
- Currency: {currency}
"""

# ── Skill Impact Analysis ──────────────────────────────────────

SKILL_IMPACTS_USER_PROMPT = """\
Quantify the salary impact of each skill in this professional's portfolio.

## Skill Portfolio
{skills_data}

## Professional Context
- Role Title: {role_title}
- Location: {location}
- Seniority Level: {seniority_level}
- Industry: {industry}

## Salary Estimate Context
- Estimated median salary: {estimated_median} {currency}
- Market percentile: {market_percentile}

## Analysis Requirements
For each skill, estimate:
- How much this specific skill adds (or subtracts) from the base salary
- The demand premium (how much extra this skill is worth due to demand)
- The scarcity factor (0-1, how rare this skill is in the talent pool)

Return JSON with this exact structure:
{{
    "impacts": [
        {{
            "skill_name": "string",
            "category": "technical | soft | tool | domain | language",
            "salary_impact_amount": float (annual EUR/year, positive or negative),
            "salary_impact_percent": float (% of base salary, positive or negative),
            "demand_premium": float (0-100, market demand for this skill),
            "scarcity_factor": float (0.0-1.0, talent scarcity),
            "impact_direction": "positive | neutral | negative",
            "reasoning": "string explaining the impact"
        }}
    ]
}}

RULES:
- salary_impact_amount can be negative (skill drags salary down)
- Sum of all impacts should approximate the skill_premium_factor
- scarcity_factor: 0.0 = very common, 1.0 = extremely rare
- Order impacts by absolute magnitude (highest impact first)
"""

# ── Salary Trajectory Projection ──────────────────────────────

SALARY_TRAJECTORY_USER_PROMPT = """\
Project this professional's salary trajectory based on their career
momentum and market conditions.

## Current Salary Estimate
- Median: {current_median} {currency}
- Market percentile: {market_percentile}
- Confidence: {confidence}

## Career Context
- Role Title: {role_title}
- Location: {location}
- Seniority Level: {seniority_level}
- Industry: {industry}

## Skill Momentum
{skill_momentum_data}

## Historical Data Points (if available)
{historical_data}

## Projection Requirements
Based on career trajectory, skill growth velocity, and market trends,
project the salary trajectory for 6 and 12 months.

Return JSON with this exact structure:
{{
    "projected_6m_median": float (projected salary in 6 months),
    "projected_12m_median": float (projected salary in 12 months),
    "trend_direction": "ascending | stable | declining",
    "trend_confidence": float (0.0-0.85),
    "reasoning": "string explaining the trajectory projection",
    "key_growth_drivers": ["factor1", "factor2"],
    "key_risk_factors": ["risk1", "risk2"]
}}

RULES:
- Projections should be CONSERVATIVE — cap growth at 15% annually
  unless there's strong evidence of promotion/role change
- trend_confidence MUST NOT exceed 0.85
- Always mention at least 1 risk factor alongside growth drivers
"""

# ── What-If Scenario Simulation ────────────────────────────────

SALARY_SCENARIO_USER_PROMPT = """\
Simulate the salary impact of a hypothetical career change.

## Current Salary Estimate
- Median: {current_median} {currency}
- Min-Max Range: {current_min} - {current_max} {currency}
- Role: {role_title} in {location}

## Current Skills
{current_skills}

## Scenario
- Type: {scenario_type}
- Label: {scenario_label}
- Details: {scenario_input}

## Simulation Requirements
Estimate what the salary range would be AFTER this change takes effect.
Consider:
- Direct impact (e.g., adding a high-demand skill)
- Indirect effects (e.g., moving to a higher/lower cost-of-living area)
- Market conditions for the changed profile
- Time to realize the impact (some changes are immediate, some take months)

Return JSON with this exact structure:
{{
    "projected_min": float (new salary lower bound),
    "projected_max": float (new salary upper bound),
    "projected_median": float (new salary best estimate),
    "delta_amount": float (change from current median),
    "delta_percent": float (% change from current median),
    "confidence": float (0.0-0.85),
    "reasoning": "string explaining the scenario impact",
    "impact_breakdown": {{
        "direct_effect": "string — primary impact description",
        "market_adjustment": "string — how this changes market positioning",
        "time_to_realize": "string — when would this impact be felt",
        "risks": ["potential risk 1", "potential risk 2"]
    }}
}}

RULES:
- delta_amount = projected_median - current_median
- delta_percent = (delta_amount / current_median) * 100
- confidence MUST NOT exceed 0.85
- Be CONSERVATIVE with impact estimates
- Always include at least 1 risk in the impact breakdown
"""
