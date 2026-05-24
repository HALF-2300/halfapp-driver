"""Backend-only engineering assistant — provider keys read from env, never exposed to clients."""
from __future__ import annotations

import os
from typing import Any

import httpx

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip()
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = os.getenv("ANTHROPIC_VERSION", "2023-06-01").strip()
HTTP_TIMEOUT_SECONDS = float(os.getenv("ENGINEERING_ASSISTANT_HTTP_TIMEOUT_SECONDS", "60"))


class ProviderNotConfiguredError(RuntimeError):
    """Raised when chat is requested but the assistant is disabled or has no provider API key."""


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_assistant_enabled() -> bool:
    """Explicit opt-in — default off so provider keys never trigger silent network calls."""
    return _truthy_env("ENGINEERING_ASSISTANT_ENABLED")


def _provider_api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "").strip()


def is_provider_configured() -> bool:
    return is_assistant_enabled() and bool(_provider_api_key())


def provider_name() -> str | None:
    return "anthropic" if is_provider_configured() else None


def _build_anthropic_messages(
    history: list[dict[str, str]],
    prompt: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in history:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt.strip()})
    return messages


def chat_with_provider(
    *,
    history: list[dict[str, str]],
    prompt: str,
    client: httpx.Client | None = None,
) -> str:
    if not is_provider_configured():
        raise ProviderNotConfiguredError("Engineering assistant provider is not configured")

    api_key = _provider_api_key()
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "messages": _build_anthropic_messages(history, prompt),
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    http = client or httpx.Client(timeout=HTTP_TIMEOUT_SECONDS)
    owns_client = client is None
    try:
        response = http.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    finally:
        if owns_client:
            http.close()

    content_blocks = body.get("content") or []
    text_parts = [
        block.get("text", "")
        for block in content_blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    reply = "\n".join(part for part in text_parts if part).strip()
    if not reply:
        raise RuntimeError("Provider returned an empty assistant reply")
    return reply
