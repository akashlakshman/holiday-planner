"""AI itinerary generation service supporting Gemini, Anthropic, and OpenAI."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from backend.config import settings
from backend.models import AIProvider, TripRequest
from backend.prompts.itinerary_prompt import build_itinerary_prompt

_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds between retries on 503


# ---------------------------------------------------------------------------
# JSON extractor
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Strip any markdown fences and parse JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

async def _generate_gemini(prompt: str) -> dict[str, Any]:
    from google import genai  # type: ignore

    client = genai.Client(api_key=settings.gemini_api_key)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return _extract_json(response.text)
        except Exception as exc:
            is_503 = "503" in str(exc) or "UNAVAILABLE" in str(exc) or "high demand" in str(exc)
            if is_503 and attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY * attempt)
                continue
            raise


async def _generate_anthropic(prompt: str) -> dict[str, Any]:
    import anthropic as anthropic_sdk  # type: ignore

    client = anthropic_sdk.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(message.content[0].text)


async def _generate_openai(prompt: str) -> dict[str, Any]:
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_itinerary(req: TripRequest) -> dict[str, Any]:
    """Generate a trip itinerary using the requested AI provider."""
    prompt = build_itinerary_prompt(req)

    if req.ai_provider == AIProvider.gemini:
        return await _generate_gemini(prompt)
    elif req.ai_provider == AIProvider.anthropic:
        return await _generate_anthropic(prompt)
    elif req.ai_provider == AIProvider.openai:
        return await _generate_openai(prompt)
    else:
        raise ValueError(f"Unknown AI provider: {req.ai_provider}")
