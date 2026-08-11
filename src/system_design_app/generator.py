"""Generates new content-bank entries via the Gemini API when the bank runs low."""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import errors, types

from system_design_app.models import Entry

logger = logging.getLogger(__name__)

GENERATION_PROMPT = """Generate {count} new system design learning entries as a JSON array.

Each entry must be an object with exactly these fields:
- "type": either "fact" or "quiz"
- "text": (only for type "fact") a single interesting, specific system design fact, 1-3 sentences
- "question" and "answer": (only for type "quiz") a system design interview-style question \
and its answer, each 1-3 sentences
- "source_url": a real, working URL to an article, paper, or documentation page that \
supports this entry
- "source_excerpt": a short paraphrase (1-2 sentences) of that source's relevant content

Mix fact and quiz types. Cover distinct system design topics (e.g. caching, load \
balancing, consistency models, sharding, queues, rate limiting, CDNs, consensus). \
Avoid duplicating any of these existing entries: {existing_summaries}

Respond with ONLY the JSON array, no other text."""


class GenerationError(RuntimeError):
    """Raised when the Gemini API fails or returns unusable content."""


def generate_entries(
    api_key: str,
    model: str,
    count: int,
    existing_entries: list[Entry],
    start_id: int,
) -> list[Entry]:
    client = genai.Client(api_key=api_key)
    existing_summaries = "; ".join(
        (e.text or e.question or "")[:80] for e in existing_entries[-20:]
    )
    prompt = GENERATION_PROMPT.format(
        count=count, existing_summaries=existing_summaries or "none"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    except errors.APIError as exc:
        raise GenerationError(f"Gemini API request failed: {exc}") from exc

    raw_text = response.text or ""

    try:
        raw_entries = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GenerationError(
            f"model did not return valid JSON: {raw_text[:200]}"
        ) from exc

    if not isinstance(raw_entries, list):
        raise GenerationError("model response was not a JSON array")

    entries: list[Entry] = []
    for offset, raw in enumerate(raw_entries):
        raw["id"] = start_id + offset
        try:
            entries.append(Entry.from_dict(raw))
        except (KeyError, ValueError) as exc:
            logger.warning("skipping malformed generated entry: %s", exc)

    logger.info("generated %d new content bank entries", len(entries))
    return entries
