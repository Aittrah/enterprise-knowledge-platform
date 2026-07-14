"""EKIP API application factory.

Run locally:
    uvicorn app.api.main:create_app --factory --reload

Keyless defaults (in-memory store, hashing embedder, extractive answers)
mean this starts on a fresh clone; .env switches on real providers.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analytics, auth, chat, documents, graph, search
from app.api.state import AppState
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Enterprise Knowledge Intelligence Platform",
        version="0.6.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.ekip = AppState(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (auth, documents, chat, search, graph, analytics):
        app.include_router(router.router, prefix="/api")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": app.version}

    return app
