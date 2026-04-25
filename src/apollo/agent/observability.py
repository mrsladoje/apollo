"""Langfuse observability glue (PLAN-C §9, ADR-016).

The intent is that ``LANGSMITH_OTEL_ENABLED=true`` plus the Langfuse SDK
publish traces to whichever ``LANGFUSE_HOST`` is set. This module exposes
helpers used by the agent loop and by the SSE encoder so the ``done`` event
always carries a usable ``trace_url`` even when Langfuse itself is offline.
"""

from __future__ import annotations

import os
import uuid


def langfuse_host() -> str:
    return os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")


def langfuse_enabled() -> bool:
    return os.environ.get("LANGSMITH_OTEL_ENABLED", "").lower() == "true" and bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
    )


def trace_url_for(query: str) -> str:
    """Deterministic deep link — falls back to ``localhost:3000`` when the
    self-hosted fallback is in use (PLAN-C §9.3).
    """
    host = langfuse_host()
    trace_id = uuid.uuid5(uuid.NAMESPACE_URL, f"apollo|{query}").hex
    return f"{host}/trace/{trace_id}"


def get_client():  # pragma: no cover — exercised only when langfuse installed
    if not langfuse_enabled():
        return None
    try:
        from langfuse import Langfuse  # type: ignore

        return Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=langfuse_host(),
        )
    except Exception:
        return None


__all__ = [
    "get_client",
    "langfuse_enabled",
    "langfuse_host",
    "trace_url_for",
]
