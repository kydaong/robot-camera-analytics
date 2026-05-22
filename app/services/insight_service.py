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

STRICT RULES:
- Only reference standards that appear VERBATIM in the <standards_context> block below.
- If no standards context is provided, set applicable_standards to [] and reference_standard to null.
- Do NOT use your training knowledge to invent or recall standards not in the context.
- Do NOT hallucinate standard numbers, clauses, or titles.

Your job:
1. Summarise the overall situation in 2-3 sentences
2. Propose concrete, prioritised maintenance actions (priority 1 = most urgent)
3. Flag if any actions require immediate shutdown or permit-to-work
4. Only cite standards explicitly found in the provided context

Return ONLY valid JSON matching the schema provided. No prose outside the JSON."""


def _highest_severity(observations: list[Observation]) -> SeverityLevel:
    order = [SeverityLevel.low, SeverityLevel.medium, SeverityLevel.high, SeverityLevel.critical]
    severities = [obs.severity for obs in observations]
    for level in reversed(order):
        if level in severities:
            return level
    return SeverityLevel.low


def _extract_standard_refs(standards: list[dict]) -> list[str]:
    """Pull source filenames as the ground-truth standard references."""
    seen, refs = set(), []
    for s in standards:
        src = s.get("source", "")
        if src and src not in seen:
            seen.add(src)
            refs.append(src.replace(".pdf", "").replace("_", " "))
    return refs


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

    # Build grounded context blocks — these are the ONLY sources Claude may cite
    standards_block = ""
    if standards:
        standards_block = "\n".join(
            f"[{s.get('source', 'unknown')} | section: {s.get('section', '')}]\n{s.get('text', '')}"
            for s in standards[:5]
        )

    incidents_block = ""
    if past_incidents:
        incidents_block = "\n".join(
            f"- {i.get('text', '')}" for i in past_incidents[:3]
        )

    # Ground-truth standard names for post-processing validation
    grounded_standards = _extract_standard_refs(standards)

    user_prompt = f"""Inspection run: {request.run_id}
Location: {request.location.site_name} / {request.location.zone}
Asset: {request.location.asset_id or 'unspecified'}
Robot: {request.robot_id}

Observations:
{observation_text}

<standards_context>
{standards_block if standards_block else "No standards retrieved — do not cite any standards."}
</standards_context>

<past_incidents_context>
{incidents_block if incidents_block else "No similar past incidents found."}
</past_incidents_context>

Return JSON exactly matching this schema:
{{
  "summary": "2-3 sentence situation summary",
  "proposed_actions": [
    {{
      "description": "specific action description",
      "priority": 1,
      "estimated_duration_hours": 2.0,
      "requires_shutdown": false,
      "reference_standard": "exact source name from standards_context above, or null"
    }}
  ],
  "similar_past_incidents": ["work order reference if found in past_incidents_context, else empty list"],
  "applicable_standards": ["exact source names from standards_context only, or empty list"]
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

    # Validate: strip any cited standard not in our grounded list
    cited = data.get("applicable_standards", [])
    if grounded_standards:
        validated_standards = [s for s in cited if any(
            g.lower() in s.lower() or s.lower() in g.lower()
            for g in grounded_standards
        )]
    else:
        validated_standards = []

    proposed_actions = [
        ProposedAction(
            description=a["description"],
            priority=max(1, min(5, int(a.get("priority", 3)))),
            estimated_duration_hours=a.get("estimated_duration_hours"),
            requires_shutdown=a.get("requires_shutdown", False),
            reference_standard=a.get("reference_standard") if grounded_standards else None,
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
        applicable_standards=validated_standards,
    )
