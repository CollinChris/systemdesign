"""Generates new content-bank entries via the Gemini API when the bank runs low.

Resilience matters more than cleverness here: the app gets one shot per day,
and for five weeks a single 503 on the wrong day meant the bank never grew.
So each call retries transient errors with backoff, then falls back to a
second model (free-tier quotas are per model), and only then gives up.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

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

# 429 = per-minute rate limit or daily quota; 5xx = "high demand" / transient.
RETRYABLE_CODES = {429, 500, 502, 503, 504}
# A model that doesn't exist for this key: no point retrying it, try the fallback.
SWITCH_MODEL_CODES = {404}


class GenerationError(RuntimeError):
    """Raised when the Gemini API fails or returns unusable content."""


def _call(client: genai.Client, model: str, prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text or ""


def _request_with_retries(
    client: genai.Client,
    models: list[str],
    prompt: str,
    max_attempts: int,
    sleep: Callable[[float], None],
) -> tuple[str, str]:
    """Try each model in order, `max_attempts` times each with backoff on
    transient errors. Returns (raw_text, model_used) or raises GenerationError
    listing every failure."""
    failures: list[str] = []
    for model in models:
        delay = 10.0
        for attempt in range(1, max_attempts + 1):
            try:
                return _call(client, model, prompt), model
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                failures.append(f"{model} attempt {attempt}: {code} {str(exc)[:80]}")
                if "PerDay" in str(exc) or code in SWITCH_MODEL_CODES:
                    # Daily quota gone or model unavailable for this key: next model.
                    logger.warning(
                        "%s unusable today (%s); trying next model", model, code
                    )
                    break
                if code not in RETRYABLE_CODES or attempt == max_attempts:
                    if code not in RETRYABLE_CODES:
                        raise GenerationError(
                            f"Gemini API request failed: {exc}"
                        ) from exc
                    break
                logger.warning(
                    "%s returned %s (attempt %d/%d); retrying in %.0fs",
                    model,
                    code,
                    attempt,
                    max_attempts,
                    delay,
                )
                sleep(delay)
                delay *= 2
    raise GenerationError(
        "Gemini API request failed on every model: " + "; ".join(failures)
    )


def generate_entries(
    api_key: str,
    model: str,
    count: int,
    existing_entries: list[Entry],
    start_id: int,
    fallback_model: str | None = None,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Entry]:
    # The SDK retries 429s silently with its own backoff; disable that so the
    # loop above owns the schedule and the logs show what happened.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )
    existing_summaries = "; ".join(
        (e.text or e.question or "")[:80] for e in existing_entries[-20:]
    )
    prompt = GENERATION_PROMPT.format(
        count=count, existing_summaries=existing_summaries or "none"
    )
    models = [model] + (
        [fallback_model] if fallback_model and fallback_model != model else []
    )

    raw_text, model_used = _request_with_retries(
        client, models, prompt, max_attempts, sleep
    )

    try:
        raw_entries = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GenerationError(
            f"{model_used} did not return valid JSON: {raw_text[:200]}"
        ) from exc

    if not isinstance(raw_entries, list):
        raise GenerationError(f"{model_used} response was not a JSON array")

    entries: list[Entry] = []
    for offset, raw in enumerate(raw_entries):
        raw["id"] = start_id + offset
        try:
            entries.append(Entry.from_dict(raw))
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("skipping malformed generated entry: %s", exc)

    if not entries:
        raise GenerationError(f"{model_used} returned no usable entries")

    logger.info(
        "generated %d new content bank entries via %s", len(entries), model_used
    )
    return entries
