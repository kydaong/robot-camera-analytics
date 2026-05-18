"""
Insight generation — synthesises observations into a full InspectionInsight report.
"""
import json

import anthropic

from app.config import settings
from app.models.schemas import (
    InspectionInsight, InspectionRequest, Observation,
    ProposedAction, SeverityLevel,
)
from app.services.context_service import get_incidents_context, get_standards_context

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

INSIGHT_SYSTEM_PROMPT = """You are an AI inspection analyst for industrial assets in Singapore.
You receive structured observations from a Spot robot camera inspection.
Your job is to:
1. Summarise the overall situation in 2-3 sentences
2. Propose concrete, prioritised maintenance actions (priority 1 = most urgent)
3. Reference applicable Singapore Standards (SS, CP, TR series) where relevant
4. Flag if any actions require immediate shutdown or permit-to-work

Return ONLY valid JSON matching the schema provided. No prose outside the JSON."""


def _highest_severity(observations: list[Observation]) -> SeverityLevel:
    order = [SeverityLevel.low, SeverityLevel.medium, SeverityLevel.high, SeverityLevel.critical]
    severities = [obs.severity for obs in observations]
    for level in reversed(order):
        if level in severities:
            return level
    return SeverityLevel.low


def generate_insight(
    request: InspectionRequest,
    observations: list[Observation],
) -> InspectionInsight:
    observation_text = "\n".join(
        f"- [{obs.severity.upper()}] {obs.description} (confidence {obs.confidence:.0%})"
        for obs in observations
    )
    query = observation_text[:500]

    past_incidents = get_incidents_context(query)
    standards = get_standards_context(query)

    context_block = ""
    if past_incidents:
        context_block += "Past similar incidents:\n" + "\n".join(
            f"- {i.get('text', '')}" for i in past_incidents[:3]
        ) + "\n\n"
    if standards:
        context_block += "Relevant standards:\n" + "\n".join(
            f"- {s.get('text', '')}" for s in standards[:3]
        )

    user_prompt = f"""Inspection run: {request.run_id}
Location: {request.location.site_name} / {request.location.zone}
Asset: {request.location.asset_id or 'unspecified'}
Robot: {request.robot_id}

Observations:
{observation_text}

{context_block}

Return JSON with:
{{
  "summary": "...",
  "proposed_actions": [
    {{
      "description": "...",
      "priority": 1-5,
      "estimated_duration_hours": 0.5,
      "requires_shutdown": false,
      "reference_standard": "SS XXX:YYYY clause N.N or null"
    }}
  ],
  "similar_past_incidents": ["...", "..."],
  "applicable_standards": ["SS XXX:YYYY", "..."]
}}"""

    response = _client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        system=INSIGHT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())

    proposed_actions = [
        ProposedAction(
            description=a["description"],
            priority=a["priority"],
            estimated_duration_hours=a.get("estimated_duration_hours"),
            requires_shutdown=a.get("requires_shutdown", False),
            reference_standard=a.get("reference_standard"),
        )
        for a in data.get("proposed_actions", [])
    ]

    return InspectionInsight(
        run_id=request.run_id,
        location=request.location,
        captured_at=request.captured_at,
        robot_id=request.robot_id,
        observations=observations,
        overall_severity=_highest_severity(observations),
        summary=data.get("summary", ""),
        proposed_actions=proposed_actions,
        similar_past_incidents=data.get("similar_past_incidents", []),
        applicable_standards=data.get("applicable_standards", []),
    )
