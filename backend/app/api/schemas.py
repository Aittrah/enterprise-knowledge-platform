"""Request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: str
    password: str


class UpdateProfileIn(BaseModel):
    email: str | None = Field(
        default=None, min_length=5, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    name: str | None = Field(default=None, min_length=1, max_length=80)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    agent_id: str | None = None
    conversation_id: str | None = None


class CitationOut(BaseModel):
    n: int
    source: str
    chunk_id: str
    heading_path: list[str] = []
    score: float


class ChatOut(BaseModel):
    conversation_id: str
    agent_id: str
    text: str
    citations: list[CitationOut]
    invalid_citations: list[int]
    grounded: bool
    retrieval_ms: float
    prompt_tokens: int
    completion_tokens: int
    guardrail: dict | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=8, ge=1, le=50)
    filters: dict | None = None


class SearchHitOut(BaseModel):
    id: str
    score: float
    text: str
    source: str
    metadata: dict


class SearchOut(BaseModel):
    query: str
    strategy: str
    elapsed_ms: float
    hits: list[SearchHitOut]
    debug: dict
