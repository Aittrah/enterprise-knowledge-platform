from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_state
from app.api.state import AppState

router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)


@router.get("/summary")
def summary(state: AppState = Depends(get_state)) -> dict:
    embedding_stats = state.embeddings.stats
    return {
        "documents": len(state.documents),
        "chunks": state.store.count(),
        "conversations": len(state.memory.conversations()),
        "queries": state.stats["queries"],
        "prompt_tokens": state.stats["prompt_tokens"],
        "completion_tokens": state.stats["completion_tokens"],
        "queries_by_agent": state.stats["by_agent"],
        "graph": state.graph.stats(),
        "embedding_cache": {
            "hits": embedding_stats["cache_hits"],
            "misses": embedding_stats["cache_misses"],
        },
        "providers": {
            "embedding": state.embeddings.provider.name,
            "llm": state.llm.name,
            "vector_store": type(state.store).__name__,
        },
    }
