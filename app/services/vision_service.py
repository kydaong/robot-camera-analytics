"""
Vision analysis — sends Spot camera images to Claude for observation extraction.
"""
import base64
from pathlib import Path

import anthropic

from app.config import settings
from app.models.schemas import Observation, SeverityLevel

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

VISION_SYSTEM_PROMPT = """You are an expert industrial inspection AI analyzing images from a Boston Dynamics Spot robot.
For each image, identify:
1. Any visible defects, anomalies, or maintenance issues
2. Severity level (low / medium / high / critical)
3. Your confidence (0.0 – 1.0)
4. A clear, factual description suitable for a maintenance report

Be concise and factual. Do not speculate beyond what is visible."""


def analyze_image(image_path: Path, asset_context: str = "") -> list[Observation]:
    """Run Claude vision on a single image and return structured observations."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    suffix = image_path.suffix.lower()
    media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    media_type = media_type_map.get(suffix, "image/jpeg")

    user_content = []
    if asset_context:
        user_content.append({"type": "text", "text": f"Asset context: {asset_context}"})
    user_content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": image_data},
    })
    user_content.append({
        "type": "text",
        "text": (
            "Analyse this image. Return a JSON array of observations, each with fields: "
            "description (string), severity (low|medium|high|critical), confidence (float 0-1). "
            "Return only valid JSON, no prose."
        ),
    })

    response = _client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=1024,
        system=VISION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    import json
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())

    return [
        Observation(
            image_filename=image_path.name,
            description=item["description"],
            severity=SeverityLevel(item["severity"]),
            confidence=float(item["confidence"]),
        )
        for item in data
    ]
