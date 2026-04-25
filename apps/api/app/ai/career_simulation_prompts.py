"""
PathForge — Career Simulation Engine™ Prompt Templates
========================================================
Versioned AI prompt templates for the Career Simulation Engine.

Each prompt follows the PathForge AI Prompt Convention:
    - VERSION identifier for reproducibility
    - Structured JSON output format
    - Hard confidence cap reminder (0.85)
    - Data transparency instructions
"""

# ── Prompt Version ────────────────────────────────────────────
PROMPT_VERSION = "career_simulation_v1"


# ── Prompt 1: Scenario Analysis ──────────────────────────────

SCENARIO_ANALYSIS_PROMPT = """You are an expert career simulation analyst.
Analyze the following "what-if" career scenario and provide evidence-based projections.

VERSION: {version}

SCENARIO TYPE: {scenario_type}

USER PROFILE (Career DNA):
- Current role: {current_role}
- Current seniority: {current_seniority}
- Current industry: {current_industry}
- Current location: {current_location}
- Key skills: {skills}
- Years of experience: {years_experience}

SCENARIO PARAMETERS:
{scenario_parameters}

INSTRUCTIONS:
1. Analyze the feasibility of this career scenario change
2. Estimate the confidence level (NEVER exceed 0.85 — this is a hard cap)
3. Calculate a feasibility rating (0-100)
4. Estimate the salary impact percentage
5. Estimate the timeline in months
6. Provide reasoning for your analysis
7. List key factors influencing the outcome

Return ONLY valid JSON in this exact format:
{{
    "confidence_score": <float 0.0-0.85>,
    "feasibility_rating": <float 0.0-100.0>,
    "salary_impact_percent": <float>,
    "estimated_months": <int>,
    "reasoning": "<string>",
    "factors": {{
        "skill_alignment": "<string>",
        "market_demand": "<string>",
        "competition_level": "<string>",
        "growth_outlook": "<string>",
        "risk_assessment": "<string>"
    }}
}}

CRITICAL: Confidence MUST NOT exceed 0.85. Be realistic and evidence-based.
All projections are estimates — frame them as such."""


# ── Prompt 2: Outcome Projection ─────────────────────────────

OUTCOME_PROJECTION_PROMPT = """You are an expert career outcome analyst.
Project specific dimensional outcomes for this career scenario.

VERSION: {version}

SCENARIO CONTEXT:
- Scenario type: {scenario_type}
- Current role: {current_role}
- Scenario parameters: {scenario_parameters}
- Analysis confidence: {confidence_score}
- Analysis reasoning: {reasoning}

INSTRUCTIONS:
Project outcomes across these dimensions:
1. salary — Annual salary change (in EUR or equivalent)
2. market_demand — Job market demand change (percentage)
3. growth_potential — Career growth trajectory change (percentage)
4. skill_gap — Number of skills needed to close the gap
5. work_life_balance — Estimated impact on work-life balance (qualitative scale)
6. job_security — Impact on job security (percentage)

Return ONLY valid JSON in this exact format:
{{
    "outcomes": [
        {{
            "dimension": "<string>",
            "current_value": <float>,
            "projected_value": <float>,
            "delta": <float>,
            "unit": "<string>",
            "reasoning": "<string>"
        }}
    ]
}}

Be realistic. Use actual market data patterns where possible.
All values must be quantifiable for comparison purposes."""


# ── Prompt 3: Recommendation Generation ──────────────────────

RECOMMENDATION_GENERATION_PROMPT = """You are an expert career advisor.
Generate actionable, prioritized recommendations for this career simulation.

VERSION: {version}

SCENARIO CONTEXT:
- Scenario type: {scenario_type}
- Current role: {current_role}
- Scenario parameters: {scenario_parameters}
- Analysis confidence: {confidence_score}
- Analysis reasoning: {reasoning}
- Projected outcomes: {outcomes_summary}

INSTRUCTIONS:
Generate 3-6 concrete, actionable recommendations. Each should:
1. Have a clear priority (critical / high / medium / nice_to_have)
2. Include a realistic time estimate in weeks (max 104 = 2 years)
3. Be specific and actionable (no generic advice)
4. Be ordered from most impactful to least impactful

Return ONLY valid JSON in this exact format:
{{
    "recommendations": [
        {{
            "priority": "<critical|high|medium|nice_to_have>",
            "title": "<string, max 255 chars>",
            "description": "<string, detailed and actionable>",
            "estimated_weeks": <int 1-104>,
            "order_index": <int 0-based>
        }}
    ]
}}

Be specific to THIS user's situation based on their Career DNA.
Do not give generic career advice."""


# ── Prompt 4: Scenario Comparison ─────────────────────────────

SCENARIO_COMPARISON_PROMPT = """You are an expert career strategy analyst.
Compare multiple career scenarios and provide a ranked recommendation.

VERSION: {version}

USER PROFILE:
- Current role: {current_role}
- Current seniority: {current_seniority}
- Current industry: {current_industry}

SCENARIOS TO COMPARE:
{scenarios_json}

INSTRUCTIONS:
1. Rank scenarios by composite desirability (considering confidence, ROI, feasibility, timeline)
2. Identify trade-offs between scenarios
3. Provide a clear, professional analysis of which scenario is most advantageous and why
4. Note any scenarios that should be combined or sequenced

Return ONLY valid JSON in this exact format:
{{
    "ranking": [<ordered list of simulation IDs by desirability>],
    "trade_off_analysis": "<detailed professional analysis of trade-offs and recommendation>"
}}

Be balanced. Acknowledge that all scenarios have merit.
Frame low-confidence scenarios as 'challenging but possible', never 'impossible'."""
