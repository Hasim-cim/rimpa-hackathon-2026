"""Anthropic client wrapper. The LLM may only split text into claims; it never decides a weight."""

from __future__ import annotations

import os

import anthropic
from pydantic import BaseModel

from .models import LLMResult

MODEL = os.environ.get("RECORDCHECK_MODEL", "claude-opus-5-5")

# model id the API returned for the most recent split_claims call (evidence.assess records it in `method`)
LAST_MODEL_RETURNED: str | None = None


class ClaimList(BaseModel):
    claims: list[str]


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def complete(prompt: str, *, system: str = "") -> LLMResult:
    response = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system or anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return LLMResult(
        text=text,
        model_requested=MODEL,
        model_returned=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


_SPLIT_PROMPT = (
    "Split the following text into atomic claims, one factual assertion each. Keep the wording verbatim. "
    "Keep any [n] citation markers attached to the sentence they belong to. Do not add, merge or "
    "paraphrase. Return the claims in document order.\n\nTEXT:\n"
)


def split_claims(text: str) -> list[str]:
    global LAST_MODEL_RETURNED
    response = _client().messages.parse(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": _SPLIT_PROMPT + text}],
        output_format=ClaimList,
    )
    LAST_MODEL_RETURNED = response.model
    parsed = response.parsed_output
    return [c.strip() for c in parsed.claims if c.strip()] if parsed else []
