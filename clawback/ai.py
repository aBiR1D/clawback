"""LLM abstraction layer supporting Anthropic Claude and OpenAI GPT."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Provider enumeration
# ---------------------------------------------------------------------------

_PROVIDER: str = os.getenv("CLAWBACK_LLM_PROVIDER", "anthropic").lower()
_ANTHROPIC_MODEL: str = os.getenv("CLAWBACK_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
_OPENAI_MODEL: str = os.getenv("CLAWBACK_OPENAI_MODEL", "gpt-4o")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_anthropic(system: str, prompt: str, *, max_tokens: int = 4096) -> str:
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=_ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai(system: str, prompt: str, *, max_tokens: int = 4096) -> str:
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=_OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def llm_call(system: str, prompt: str, *, max_tokens: int = 4096) -> str:
    """Send a prompt to the configured LLM and return raw text."""
    if _PROVIDER == "openai":
        return _call_openai(system, prompt, max_tokens=max_tokens)
    return _call_anthropic(system, prompt, max_tokens=max_tokens)


def llm_json(system: str, prompt: str, *, max_tokens: int = 4096) -> dict[str, Any]:
    """Send a prompt expecting JSON back; parse and return a dict.

    The prompt is augmented to request JSON output. If the LLM wraps the
    response in markdown fences they are stripped automatically.
    """
    json_instruction = (
        "\n\nRespond ONLY with valid JSON. No markdown fences, no commentary."
    )
    raw = llm_call(system, prompt + json_instruction, max_tokens=max_tokens)
    cleaned = _strip_json_fences(raw)
    return json.loads(cleaned)


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[: -3]
    return text.strip()
