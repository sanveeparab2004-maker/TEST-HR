import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("assess.ai_summary")


async def generate_ai_summary(
    employee_code: str,
    band: str,
    section_scores: Dict[str, Any],
    missed_topics: List[str]
) -> Dict[str, Any]:
    """Generates structured professional development advisory using Claude API.
    
    Privacy rule: Only employee code, scores, band, and missed topics are sent.
    No PII or candidate names are ever transmitted.
    """
    api_key = settings.ANTHROPIC_API_KEY

    # If Anthropic API key is not configured, generate rule-based development guidance
    if not api_key:
        return _generate_fallback_summary(band, section_scores, missed_topics)

    prompt = f"""
You are an expert HR Development and Talent Analytics Advisor.
Analyze the following assessment results for employee {employee_code}:
- Overall Performance Band: {band}
- Section Performance Breakdown: {json.dumps(section_scores)}
- Areas / Question Topics Missed: {json.dumps(missed_topics[:10])}

Provide a short, constructive, professional development recommendation.
Do NOT mention candidate honesty, integrity, proctoring, or marks alteration.
Return ONLY valid JSON matching this exact structure:
{{
  "strengths": ["string", "string"],
  "weak_areas": ["string", "string"],
  "recommended_training": ["string", "string"],
  "summary_note": "A 2-sentence encouraging professional summary."
}}
"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": settings.CLAUDE_MODEL,
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            if res.status_code == 200:
                data = res.json()
                content_text = data["content"][0]["text"].strip()
                # Extract JSON if wrapped in markdown fences
                if "```json" in content_text:
                    content_text = content_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```", 1)[1].split("```", 1)[0].strip()
                return json.loads(content_text)
            else:
                logger.warning(f"Claude API returned status {res.status_code}")
                return _generate_fallback_summary(band, section_scores, missed_topics)
    except Exception as e:
        logger.warning(f"Error calling Claude API: {e}")
        return _generate_fallback_summary(band, section_scores, missed_topics)


def _generate_fallback_summary(
    band: str,
    section_scores: Dict[str, Any],
    missed_topics: List[str]
) -> Dict[str, Any]:
    """Deterministic fallback guidance based on scores when Claude API is not configured."""
    strengths = []
    weak_areas = []

    for s_name, data in section_scores.items():
        pct = data.get("percentage", 0)
        if pct >= 70:
            strengths.append(f"Demonstrated solid competency in {s_name} ({pct:.0f}% proficiency)")
        elif pct < 60:
            weak_areas.append(f"Requires deeper procedural grounding in {s_name} ({pct:.0f}%)")

    if not strengths:
        strengths.append("Foundational understanding of core Talent Acquisition & HR operations concepts")
    if not weak_areas:
        weak_areas.append("Opportunity for specialized masterclasses and advanced MIS automation")

    recommended = [
        "Advanced Excel formulas & automated HR MIS dashboarding workshop",
        "Statutory compliance and POSH inquiry best practice refresher"
    ]

    return {
        "strengths": strengths[:3],
        "weak_areas": weak_areas[:3],
        "recommended_training": recommended,
        "summary_note": f"Candidate demonstrated performance categorized under {band}. Targeted development in flagged topics will accelerate domain mastery.",
        "is_advisory": True,
        "source": "Rules-based fallback (Configure ANTHROPIC_API_KEY for Claude LLM insights)"
    }
