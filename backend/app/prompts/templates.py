"""Prompt templates with declared, validated variables.

A template that silently renders with a missing variable ships a broken
prompt to production; here it raises at render time instead.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field


class TemplateError(Exception):
    """A template was rendered with missing or unknown variables."""


_FIELD = string.Formatter()


def _variables(template: str) -> frozenset[str]:
    return frozenset(
        name for _, name, _, _ in _FIELD.parse(template) if name
    )


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    system: str
    user: str
    description: str = ""
    variables: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "variables", _variables(self.system) | _variables(self.user)
        )

    def render(self, **values: object) -> list[dict[str, str]]:
        """Return chat messages ([{role, content}, ...]) with all variables
        substituted; missing or unknown variables raise ``TemplateError``."""
        missing = self.variables - values.keys()
        if missing:
            raise TemplateError(
                f"template '{self.name}' missing variables: {sorted(missing)}"
            )
        unknown = values.keys() - self.variables
        if unknown:
            raise TemplateError(
                f"template '{self.name}' got unknown variables: {sorted(unknown)}"
            )
        return [
            {"role": "system", "content": self.system.format(**values)},
            {"role": "user", "content": self.user.format(**values)},
        ]


def escape_braces(text: str) -> str:
    """Make arbitrary text safe to embed in a template value."""
    return re.sub(r"([{}])", r"\1\1", text)
