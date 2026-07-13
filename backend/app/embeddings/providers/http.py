"""Shared HTTP plumbing for REST embedding providers.

Adapters speak plain REST via httpx rather than per-vendor SDKs: one
dependency, uniform error handling, and tests can inject a MockTransport.
"""

from __future__ import annotations

import os

import httpx

from app.embeddings.base import ProviderConfigurationError, ProviderRequestError


def require_api_key(env_var: str, explicit: str | None) -> str:
    key = explicit or os.environ.get(env_var, "").strip()
    if not key:
        raise ProviderConfigurationError(
            f"API key missing: pass api_key= or set {env_var} in the environment/.env"
        )
    return key


def post_json(
    client: httpx.Client, url: str, headers: dict[str, str], payload: dict
) -> dict:
    try:
        response = client.post(url, headers=headers, json=payload, timeout=60.0)
    except httpx.HTTPError as exc:
        raise ProviderRequestError(f"request to {url} failed: {exc}") from exc
    if response.status_code != 200:
        raise ProviderRequestError(
            f"{url} returned {response.status_code}: {response.text[:300]}"
        )
    return response.json()
