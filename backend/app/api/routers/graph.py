from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_state
from app.api.state import AppState

router = APIRouter(
    prefix="/graph", tags=["graph"], dependencies=[Depends(get_current_user)]
)


@router.get("/viz")
def visualization(state: AppState = Depends(get_state)) -> dict:
    return state.graph.to_visualization()


@router.get("/search")
def search_nodes(
    q: str = Query(min_length=1), state: AppState = Depends(get_state)
) -> list[dict]:
    return [
        {"key": e.key, "label": e.text, "type": e.type, "mentions": e.mentions}
        for e in state.graph.search_nodes(q)
    ]


@router.get("/neighbors")
def neighbors(
    key: str,
    depth: int = Query(default=1, ge=1, le=3),
    state: AppState = Depends(get_state),
) -> dict:
    result = state.graph.neighbors(key, depth=depth)
    return {
        "nodes": [
            {"key": e.key, "label": e.text, "type": e.type} for e in result["nodes"]
        ],
        "edges": [
            {
                "source": r.source_key,
                "target": r.target_key,
                "type": r.type,
                "evidence": r.evidence,
            }
            for r in result["edges"]
        ],
    }


@router.get("/stats")
def stats(state: AppState = Depends(get_state)) -> dict:
    return state.graph.stats()
