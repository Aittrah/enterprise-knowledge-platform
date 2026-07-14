import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user, get_state
from app.api.schemas import ChatIn, ChatOut, CitationOut
from app.api.state import AppState
from app.core.security import TokenError, decode_access_token

router = APIRouter(prefix="/chat", tags=["chat"])


def _to_chat_out(answer, conversation_id: str) -> ChatOut:
    return ChatOut(
        conversation_id=conversation_id,
        agent_id=answer.agent_id,
        text=answer.text,
        citations=[CitationOut(**c) for c in answer.citations],
        invalid_citations=answer.invalid_citations,
        grounded=answer.grounded,
        retrieval_ms=answer.retrieval_ms,
        prompt_tokens=answer.prompt_tokens,
        completion_tokens=answer.completion_tokens,
        guardrail=answer.guardrail,
    )


@router.post("", response_model=ChatOut, dependencies=[Depends(get_current_user)])
def chat(body: ChatIn, state: AppState = Depends(get_state)) -> ChatOut:
    try:
        answer, conversation_id = state.ask(
            body.question, body.agent_id, body.conversation_id
        )
    except ValueError as exc:  # unknown agent id
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _to_chat_out(answer, conversation_id)


@router.get("/agents", dependencies=[Depends(get_current_user)])
def agents(state: AppState = Depends(get_state)) -> list[dict]:
    return [
        {"id": p.id, "name": p.name, "description": p.description}
        for p in state.orchestrator.agents
    ]


@router.get("/conversations", dependencies=[Depends(get_current_user)])
def conversations(state: AppState = Depends(get_state)) -> list[str]:
    return state.memory.conversations()


@router.get("/conversations/{conversation_id}", dependencies=[Depends(get_current_user)])
def conversation_history(
    conversation_id: str, state: AppState = Depends(get_state)
) -> list[dict]:
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at}
        for m in state.memory.conversation(conversation_id).history()
    ]


# --- WebSocket streaming ---------------------------------------------------------

_STREAM_CHUNK_WORDS = 4


async def _stream_answer(websocket: WebSocket, state: AppState, payload: dict) -> None:
    answer, conversation_id = await run_in_threadpool(
        state.ask,
        payload["question"],
        payload.get("agent_id"),
        payload.get("conversation_id"),
    )
    await websocket.send_json(
        {"type": "start", "conversation_id": conversation_id, "agent_id": answer.agent_id}
    )
    words = answer.text.split(" ")
    for i in range(0, len(words), _STREAM_CHUNK_WORDS):
        token = " ".join(words[i : i + _STREAM_CHUNK_WORDS])
        if i + _STREAM_CHUNK_WORDS < len(words):
            token += " "
        await websocket.send_json({"type": "token", "text": token})
        await asyncio.sleep(0)  # yield so tokens flush individually
    await websocket.send_json(
        {
            "type": "done",
            "conversation_id": conversation_id,
            "agent_id": answer.agent_id,
            "citations": answer.citations,
            "invalid_citations": answer.invalid_citations,
            "grounded": answer.grounded,
            "retrieval_ms": answer.retrieval_ms,
        }
    )


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    state: AppState = websocket.app.state.ekip
    token = websocket.query_params.get("token", "")
    try:
        payload = decode_access_token(token, state.settings.jwt_secret)
        state.users.get(int(payload["sub"]))
    except (TokenError, KeyError, ValueError):
        await websocket.close(code=4401, reason="Invalid token")
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
                if not message.get("question"):
                    raise ValueError("missing 'question'")
                await _stream_answer(websocket, state, message)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
    except WebSocketDisconnect:
        return
