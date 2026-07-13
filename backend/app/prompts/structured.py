"""Structured (JSON) output: instructions in, tolerant extraction out."""

from __future__ import annotations

import json
import re


def json_output_rules(schema: dict) -> str:
    """Instruction block telling the model to answer as JSON matching *schema*."""
    return (
        "Respond with a single JSON object and nothing else - no prose, no "
        "markdown fences. It must match this schema exactly:\n"
        + json.dumps(schema, indent=2)
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict | list:
    """Parse JSON from a model reply, tolerating markdown fences and
    surrounding prose. Raises ``ValueError`` when no JSON can be found."""
    candidates = [text.strip()]
    candidates.extend(m.strip() for m in _FENCE.findall(text))
    # Last resort: first {...} or [...] span in the reply.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if 0 <= start < end:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no parseable JSON in model reply: {text[:200]!r}")
