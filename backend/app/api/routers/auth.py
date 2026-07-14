from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_state, require_admin
from app.api.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.api.state import AppState
from app.api.users import User, UserExistsError
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User, state: AppState) -> TokenOut:
    token = create_access_token(
        user.id,
        user.email,
        user.role,
        state.settings.jwt_secret,
        state.settings.jwt_expire_minutes,
    )
    return TokenOut(access_token=token, user=UserOut(**user.__dict__ | {}))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, state: AppState = Depends(get_state)) -> TokenOut:
    try:
        user = state.users.create(body.email, body.password, body.name)
    except UserExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _token_for(user, state)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, state: AppState = Depends(get_state)) -> TokenOut:
    user = state.users.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return _token_for(user, state)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_admin), state: AppState = Depends(get_state)
) -> list[UserOut]:
    return [
        UserOut(id=u.id, email=u.email, name=u.name, role=u.role)
        for u in state.users.list()
    ]
