"""
PathForge — Career Action Planner™ Prompt Templates
=====================================================
Versioned prompt templates for the Career Action Planner AI pipeline.

Prompts:
    CAREER_PRIORITIES_PROMPT     — Analyze and rank career priorities
    MILESTONE_GENERATION_PROMPT  — Generate actionable milestones
    PROGRESS_EVALUATION_PROMPT   — Assess progress and recalculate
    RECOMMENDATIONS_PROMPT       — Cross-engine recommendation generation
"""

# ── Career Priorities Analysis ─────────────────────────────────

CAREER_PRIORITIES_PROMPT = """You are an expert career strategist analyzing a professional's career data
to identify and rank their top career priorities.

## Professional Profile
- Primary Role: {primary_role}
- Industry: {primary_industry}
- Seniority: {seniority_level}
- Location: {location}
- Skills: {skills}

## Plan Type Requested
{plan_type}

## Additional Focus
{focus_area}

## Career Intelligence Summary
{intelligence_summary}

## Instructions
Analyze the professional profile and intelligence data to identify the top 5
career priorities ranked by urgency and potential impact. For each priority:

1. Identify the specific career gap or opportunity
2. Assess urgency (critical, high, medium, low)
3. Estimate potential impact on career trajectory
4. Suggest the primary action category (learning, certification, networking,
   project, application, interview_prep)

IMPORTANT CONSTRAINTS:
- Do NOT make assumptions about the user's demographics
- Do NOT recommend specific products or paid services by name
- Focus on actionable, measurable priorities
- Base urgency on market data, not speculation

Return a JSON object with this exact structure:
{{
    "priorities": [
        {{
            "title": "string — concise priority title",
            "description": "string — what needs to be done and why",
            "urgency": "critical|high|medium|low",
            "impact_score": 0.0-100.0,
            "category": "learning|certification|networking|project|application|interview_prep",
            "rationale": "string — data-driven reasoning"
        }}
    ],
    "overall_assessment": "string — brief career trajectory assessment",
    "confidence": 0.0-0.85
}}
"""

# ── Milestone Generation ───────────────────────────────────────

MILESTONE_GENERATION_PROMPT = """You are an expert career coach creating actionable milestones
for a career action plan using sprint methodology.

## Professional Profile
- Primary Role: {primary_role}
- Seniority: {seniority_level}
- Skills: {skills}

## Plan Context
- Plan Type: {plan_type}
- Plan Title: {plan_title}
- Plan Objective: {plan_objective}
- Sprint Length: {sprint_weeks} weeks
- Maximum Milestones: {max_milestones}

## Priorities to Address
{priorities_json}

## Instructions
Generate concrete, time-bound milestones for a {sprint_weeks}-week career sprint.
Each milestone must be:

1. Specific and measurable (not vague)
2. Achievable within the sprint timeframe
3. Connected to the identified priorities
4. Include effort estimates in hours
5. Define what evidence proves completion

IMPORTANT CONSTRAINTS:
- Maximum {max_milestones} milestones per plan
- Effort estimates must be realistic (not exceed 40 hours/week)
- Each milestone must have clear success criteria
- Priorities should be numbered 1 (highest) to {max_milestones} (lowest)
- Do NOT recommend specific paid products by brand name

Return a JSON object with this exact structure:
{{
    "milestones": [
        {{
            "title": "string — concise milestone title",
            "description": "string — detailed description",
            "category": "learning|certification|networking|project|application|interview_prep",
            "effort_hours": 1-120,
            "priority": 1-10,
            "evidence_required": "string — what proves completion",
            "target_week": 1-{sprint_weeks}
        }}
    ],
    "sprint_summary": "string — brief sprint objective",
    "confidence": 0.0-0.85
}}
"""

# ── Progress Evaluation ────────────────────────────────────────

PROGRESS_EVALUATION_PROMPT = """You are an expert career coach evaluating progress
on a career action plan and recalculating priorities.

## Plan Summary
- Title: {plan_title}
- Type: {plan_type}
- Sprint Length: {sprint_weeks} weeks

## Current Milestones and Progress
{milestones_json}

## Career Intelligence Updates
{intelligence_updates}

## Instructions
Evaluate the current progress and provide:

1. Overall plan health assessment
2. Which milestones are on track, at risk, or behind
3. Recommended priority adjustments based on new intelligence data
4. Suggested new actions if career events have occurred

IMPORTANT CONSTRAINTS:
- Be encouraging but honest about progress
- Do NOT lower standards to make progress look better
- Confidence must not exceed 0.85

Return a JSON object with this exact structure:
{{
    "plan_health": "on_track|at_risk|behind|ahead",
    "overall_progress_percent": 0.0-100.0,
    "milestone_assessments": [
        {{
            "milestone_id": "string — UUID",
            "status_assessment": "on_track|at_risk|behind|completed",
            "recommendation": "string — specific advice"
        }}
    ],
    "priority_adjustments": [
        {{
            "description": "string — what should change",
            "reason": "string — why, based on data"
        }}
    ],
    "confidence": 0.0-0.85
}}
"""

# ── Cross-Engine Recommendations ──────────────────────────────

RECOMMENDATIONS_PROMPT = """You are an expert career intelligence analyst generating
personalized recommendations by cross-referencing multiple career intelligence engines.

## Professional Profile
- Primary Role: {primary_role}
- Industry: {primary_industry}
- Seniority: {seniority_level}

## Active Plan Context
- Plan Type: {plan_type}
- Plan Title: {plan_title}

## Intelligence Engine Outputs
{engine_outputs}

## Instructions
Cross-reference the intelligence engine outputs to generate actionable
recommendations that enhance the active career plan. Each recommendation must:

1. Cite the specific intelligence engine it draws from
2. Explain the urgency and impact
3. Be directly actionable (not vague advice)
4. Include context data linking back to the source

IMPORTANT CONSTRAINTS:
- Maximum 5 recommendations per analysis
- Each must reference a specific source engine
- Impact scores range 0-100
- Urgency levels: critical, high, medium, low
- Do NOT repeat information already in the plan

Return a JSON object with this exact structure:
{{
    "recommendations": [
        {{
            "source_engine": "threat_radar|skill_decay|salary_intelligence|transition_pathways|career_simulation|hidden_job_market|predictive_career|collective_intelligence",
            "recommendation_type": "string — action category",
            "title": "string — concise title",
            "rationale": "string — data-driven reasoning",
            "urgency": "critical|high|medium|low",
            "impact_score": 0.0-100.0
        }}
    ],
    "confidence": 0.0-0.85
}}
"""
