from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.deps import get_current_user, get_state
from app.api.state import AppState

router = APIRouter(
    prefix="/monitoring", tags=["monitoring"], dependencies=[Depends(get_current_user)]
)


@router.get("/metrics")
def metrics(state: AppState = Depends(get_state)) -> dict:
    return state.metrics.snapshot()


@router.get("/prometheus", response_class=PlainTextResponse)
def prometheus(state: AppState = Depends(get_state)) -> str:
    return state.metrics.prometheus_text()
