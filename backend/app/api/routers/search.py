from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_state
from app.api.schemas import SearchHitOut, SearchIn, SearchOut
from app.api.state import AppState

router = APIRouter(
    prefix="/search", tags=["search"], dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=SearchOut)
def search(body: SearchIn, state: AppState = Depends(get_state)) -> SearchOut:
    result = state.retriever.retrieve(
        body.query, top_k=body.top_k, filters=body.filters
    )
    return SearchOut(
        query=result.query,
        strategy=result.strategy,
        elapsed_ms=result.elapsed_ms,
        hits=[
            SearchHitOut(
                id=c.id, score=c.score, text=c.text, source=c.source, metadata=c.metadata
            )
            for c in result.chunks
        ],
        debug=result.debug,
    )
