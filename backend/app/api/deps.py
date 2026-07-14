"""FastAPI dependencies: state access and JWT auth."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.state import AppState
from app.api.users import User
from app.core.security import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_state(request: Request) -> AppState:
    return request.app.state.ekip


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    state: AppState = Depends(get_state),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(
            credentials.credentials, state.settings.jwt_secret
        )
        return state.users.get(int(payload["sub"]))
    except (TokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
