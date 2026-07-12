"""Content-hash based version tracking.

A document is identified by a *key* (its filename by default, or an explicit
document id once the API layer exists). Re-ingesting identical bytes is a
duplicate; re-ingesting changed bytes creates the next version, which
supersedes prior chunks downstream.

Storage is a JSON file for Milestone 4; the interface is deliberately small
so it can be re-backed by PostgreSQL at Milestone 9 without touching callers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.models import VersionInfo


class VersionTracker:
    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._store: dict[str, list[dict]] = {}
        if store_path.exists():
            self._store = json.loads(store_path.read_text(encoding="utf-8"))

    def register(self, key: str, sha256: str) -> VersionInfo:
        """Record an ingestion of *key* with content hash *sha256*."""
        versions = self._store.setdefault(key, [])
        for v in versions:
            if v["sha256"] == sha256:
                return VersionInfo(
                    document_key=key,
                    version=v["version"],
                    sha256=sha256,
                    ingested_at=v["ingested_at"],
                    is_new_version=False,
                    is_duplicate=True,
                )

        entry = {
            "version": len(versions) + 1,
            "sha256": sha256,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        versions.append(entry)
        self._save()
        return VersionInfo(
            document_key=key,
            version=entry["version"],
            sha256=sha256,
            ingested_at=entry["ingested_at"],
            is_new_version=entry["version"] > 1,
            is_duplicate=False,
        )

    def history(self, key: str) -> list[dict]:
        return list(self._store.get(key, []))

    def latest_version(self, key: str) -> int:
        versions = self._store.get(key)
        return versions[-1]["version"] if versions else 0

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._store, indent=2), encoding="utf-8")
        tmp.replace(self._store_path)
