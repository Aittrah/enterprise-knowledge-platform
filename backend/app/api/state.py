"""AppState: one place where the whole platform is wired together.

Defaults are keyless and serviceless (in-memory store + hashing embedder +
extractive answers); environment settings switch on Qdrant, real embedding
providers, and a real LLM.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.agents import AgentOrchestrator
from app.agents.llm import OpenAICompatibleClient
from app.api.fallback import ExtractiveLLM
from app.api.users import UserStore
from app.core.config import Settings
from app.embeddings import EmbeddingService, create_provider
from app.graph import GraphBuilder, InMemoryGraphStore
from app.ingestion import IngestionPipeline
from app.memory import MemoryService
from app.retrieval import BM25Index, GraphRAGRetriever, HybridRetriever
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer, QdrantVectorStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        data = settings.data_dir
        data.mkdir(parents=True, exist_ok=True)
        self.upload_dir = data / "uploads"
        self.upload_dir.mkdir(exist_ok=True)

        self.users = UserStore(data / "users.db")
        self.memory = MemoryService(data / "memory.db")

        self.embeddings = EmbeddingService(
            create_provider(settings.embedding_provider),
            cache_path=data / "embeddings.db",
        )
        if settings.vector_store == "qdrant":
            self.store = QdrantVectorStore(base_url=settings.qdrant_url)
        else:
            self.store = InMemoryVectorStore()
        self.bm25 = BM25Index()
        self.indexer = KnowledgeBaseIndexer(
            self.store, self.embeddings, text_index=self.bm25
        )
        self.graph = InMemoryGraphStore()
        self.graph_builder = GraphBuilder(self.graph)

        hybrid = HybridRetriever(self.store, self.embeddings, self.bm25)
        self.retriever = GraphRAGRetriever(hybrid, self.graph)

        if settings.openai_api_key:
            self.llm = OpenAICompatibleClient(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                base_url=settings.llm_base_url,
            )
        else:
            self.llm = ExtractiveLLM()
        self.orchestrator = AgentOrchestrator(self.retriever, self.llm)

        self.pipeline = IngestionPipeline(data / "versions.json")

        self._lock = threading.Lock()
        self.documents: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.stats = {
            "queries": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "by_agent": {},
        }

    # -- ingestion jobs (BackgroundTasks worker) ---------------------------------

    def create_job(self, filename: str) -> str:
        job_id = uuid.uuid4().hex[:12]
        self.jobs[job_id] = {
            "id": job_id,
            "filename": filename,
            "status": "queued",
            "created_at": _now(),
            "error": None,
        }
        return job_id

    def run_ingestion(self, job_id: str, path: Path, filename: str) -> None:
        job = self.jobs[job_id]
        job["status"] = "running"
        try:
            result = self.pipeline.ingest(path, document_key=filename)
            index_report = self.indexer.index(result.document, result.metadata)
            graph_report = self.graph_builder.build(result.document, result.metadata)
            with self._lock:
                self.documents[filename] = {
                    "filename": filename,
                    "title": result.metadata.title,
                    "file_type": result.metadata.file_type,
                    "size_bytes": result.metadata.size_bytes,
                    "version": result.version.version,
                    "chunks": index_report.chunks_indexed,
                    "entities": graph_report.entities,
                    "warnings": result.document.warnings,
                    "indexed_at": _now(),
                }
            job["status"] = "completed"
            job["document"] = self.documents[filename]
        except Exception as exc:  # surface, never swallow
            job["status"] = "failed"
            job["error"] = str(exc)

    # -- chat -------------------------------------------------------------------------

    def ask(self, question: str, agent_id: str | None, conversation_id: str | None):
        conversation_id = conversation_id or uuid.uuid4().hex[:12]
        convo = self.memory.conversation(conversation_id)
        convo.add("user", question)

        answer = self.orchestrator.ask(question, agent_id=agent_id)
        convo.add("assistant", answer.text)

        with self._lock:
            self.stats["queries"] += 1
            self.stats["prompt_tokens"] += answer.prompt_tokens
            self.stats["completion_tokens"] += answer.completion_tokens
            self.stats["by_agent"][answer.agent_id] = (
                self.stats["by_agent"].get(answer.agent_id, 0) + 1
            )
        return answer, conversation_id
