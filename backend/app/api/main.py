"""EKIP API application factory.

Run locally:
    uvicorn app.api.main:create_app --factory --reload

Keyless defaults (in-memory store, hashing embedder, extractive answers)
mean this starts on a fresh clone; .env switches on real providers.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analytics, auth, chat, documents, graph, monitoring, search
from app.api.state import AppState
from app.core.config import Settings
from app.observability import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging()
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

    for router in (auth, documents, chat, search, graph, analytics, monitoring):
        app.include_router(router.router, prefix="/api")

    @app.middleware("http")
    async def record_request_metrics(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        labels = {
            "method": request.method,
            "path": request.url.path,
            "status": str(response.status_code),
        }
        state: AppState = app.state.ekip
        state.metrics.increment("ekip_http_requests_total", labels=labels)
        state.metrics.observe(
            "ekip_http_request_ms", elapsed_ms, labels={"path": request.url.path}
        )
        return response

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": app.version}

    return app
