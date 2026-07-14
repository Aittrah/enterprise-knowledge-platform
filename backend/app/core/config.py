"""Application settings from the environment (.env-compatible).

Every setting has a working keyless/serviceless default so `uvicorn
app.api.main:create_app --factory` runs on a fresh clone; environment
variables switch on the real backends.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path("data"))
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 480
    embedding_provider: str = "hashing"  # openai | cohere | voyage | bge | e5 | hashing
    vector_store: str = "memory"  # memory | qdrant
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    max_upload_mb: int = 100

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ
        return cls(
            data_dir=Path(env.get("EKIP_DATA_DIR", "data")),
            jwt_secret=env.get("JWT_SECRET", cls.jwt_secret),
            jwt_expire_minutes=int(env.get("JWT_EXPIRE_MINUTES", "480")),
            embedding_provider=env.get("EMBEDDING_PROVIDER", "hashing"),
            vector_store=env.get("VECTOR_STORE", "memory"),
            qdrant_url=env.get("QDRANT_URL", cls.qdrant_url),
            openai_api_key=env.get("OPENAI_API_KEY", ""),
            llm_model=env.get("LLM_MODEL", cls.llm_model),
            llm_base_url=env.get("LLM_BASE_URL", cls.llm_base_url),
            cors_origins=tuple(
                o.strip()
                for o in env.get("CORS_ORIGINS", ",".join(cls.cors_origins)).split(",")
                if o.strip()
            ),
            max_upload_mb=int(env.get("MAX_UPLOAD_MB", "100")),
        )
