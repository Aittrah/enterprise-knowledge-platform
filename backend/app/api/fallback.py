"""ExtractiveLLM: keyless answer fallback.

When no LLM API key is configured, answers are assembled extractively from
the retrieved source blocks — properly cited, honestly labeled. The whole
platform stays demo-able on a fresh clone; a real key upgrades answer
quality without touching any other code.
"""

from __future__ import annotations

import re
import textwrap

from app.agents.llm import LLMReply

# Matches the numbered blocks produced by app.prompts.context.format_context.
_BLOCK = re.compile(
    r"\[(\d+)\][^\n]*\n(.*?)(?=\n\n---\n\n|\n\nKnown relationships|\n\nQuestion:|\Z)",
    re.DOTALL,
)


class ExtractiveLLM:
    name = "extractive-fallback"
    model = "extractive"

    def chat(self, messages, temperature: float = 0.2) -> LLMReply:
        prompt = messages[-1]["content"]
        blocks = [(n, text.strip()) for n, text in _BLOCK.findall(prompt) if text.strip()]
        if not blocks:
            return LLMReply(
                text="The indexed documents don't appear to cover this question."
            )
        parts = [
            f"{textwrap.shorten(text, width=400, placeholder=' …')} [{number}]"
            for number, text in blocks[:2]
        ]
        answer = (
            "**Most relevant passages** (extractive mode — configure an LLM API "
            "key for synthesized answers):\n\n" + "\n\n".join(parts)
        )
        return LLMReply(text=answer)
