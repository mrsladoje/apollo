"""SSE helpers — wraps sse-starlette enforcing the frozen event schema (ADR-017, PLAN-C §5.2)."""

from __future__ import annotations

import json
from typing import AsyncIterator

from sse_starlette.sse import EventSourceResponse

ALLOWED_TYPES = frozenset(
    {"text-delta", "tool-call-start", "tool-result", "citation", "done"}
)


async def event_stream(events: AsyncIterator[dict]) -> EventSourceResponse:
    async def gen():
        async for ev in events:
            if ev.get("type") not in ALLOWED_TYPES:
                continue
            yield {"event": "message", "data": json.dumps(ev)}

    return EventSourceResponse(
        gen(),
        headers={"Cache-Control": "no-cache"},
        ping=15,
    )
