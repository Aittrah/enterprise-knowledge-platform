"""Golden dataset: questions with known-relevant sources and expected

answer keywords. JSON on disk so cases are reviewable diffs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class EvalCase:
    question: str
    relevant_sources: list[str]
    expected_keywords: list[str] = field(default_factory=list)
    agent_id: str | None = None


@dataclass
class GoldenDataset:
    name: str
    cases: list[EvalCase] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.cases)

    @classmethod
    def load(cls, path: Path) -> GoldenDataset:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", path.stem),
            cases=[EvalCase(**case) for case in data["cases"]],
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"name": self.name, "cases": [asdict(c) for c in self.cases]},
                indent=2,
            ),
            encoding="utf-8",
        )
