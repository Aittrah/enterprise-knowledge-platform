"""Embeddable chat widget.

Any signed-in user can mint a *widget key* — a long-lived, narrowly-scoped
token safe to paste into a `<script>` tag on someone else's website. It can
only open the widget chat socket below; it is explicitly rejected by every
dashboard endpoint (see ``deps.get_current_user``), so a key copied out of a
page's HTML source can never reach documents, admin, or profile routes.

No REST fallback is provided on purpose: a WebSocket handshake is not
subject to the browser's CORS/Fetch algorithm, so the socket embeds on any
origin with zero server-side CORS configuration — one less thing to get
wrong on a public endpoint.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user, get_state
from app.api.routers.chat import _stream_answer
from app.api.schemas import CreateWidgetKeyIn, WidgetKeyCreatedOut, WidgetKeyOut
from app.api.state import AppState
from app.api.users import User
from app.core.security import TokenError, create_widget_token, decode_access_token

router = APIRouter(tags=["widget"])


@router.post(
    "/widget-keys",
    response_model=WidgetKeyCreatedOut,
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
def create_widget_key(
    body: CreateWidgetKeyIn,
    user: User = Depends(get_current_user),
    state: AppState = Depends(get_state),
) -> WidgetKeyCreatedOut:
    key = state.widget_keys.create(user.id, body.label)
    token = create_widget_token(user.id, key.kid, state.settings.jwt_secret)
    return WidgetKeyCreatedOut(
        kid=key.kid, label=key.label, created_at=key.created_at, revoked=False, token=token
    )


@router.get(
    "/widget-keys", response_model=list[WidgetKeyOut], dependencies=[Depends(get_current_user)]
)
def list_widget_keys(
    user: User = Depends(get_current_user), state: AppState = Depends(get_state)
) -> list[WidgetKeyOut]:
    return [
        WidgetKeyOut(kid=k.kid, label=k.label, created_at=k.created_at, revoked=k.revoked)
        for k in state.widget_keys.list(user.id)
    ]


@router.delete("/widget-keys/{kid}", status_code=204, dependencies=[Depends(get_current_user)])
def revoke_widget_key(
    kid: str, user: User = Depends(get_current_user), state: AppState = Depends(get_state)
) -> None:
    if not state.widget_keys.revoke(kid, user.id):
        raise HTTPException(status_code=404, detail=f"No widget key '{kid}' for this account")


@router.websocket("/widget/chat/ws")
async def widget_chat_ws(websocket: WebSocket) -> None:
    state: AppState = websocket.app.state.ekip
    token = websocket.query_params.get("key", "")
    try:
        payload = decode_access_token(token, state.settings.jwt_secret)
        if payload.get("scope") != "widget":
            raise TokenError("not a widget key")
        if not state.widget_keys.is_active(payload["kid"]):
            raise TokenError("widget key revoked")
    except (TokenError, KeyError, ValueError):
        await websocket.close(code=4401, reason="Invalid or revoked widget key")
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
