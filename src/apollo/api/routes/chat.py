"""Chat route — POST /api/chat returns SSE stream (PLAN-C §5.1).

Behaviour:
  * APOLLO_AGENT=mock         → canned ``stream_mock_events`` from agent_mock
  * APOLLO_AGENT=loop (default) → real Apollo agent loop, deterministic seed
                                  path falls back gracefully when DSPy/Gemma
                                  aren't installed locally.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

from apollo.agent.loop import AgentLoop
from apollo.api.sse import event_stream
from apollo.mocks.agent_mock import stream_mock_events

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    query: str
    run_context: str | None = None


def _agent_mode() -> str:
    return os.environ.get("APOLLO_AGENT", "loop").lower()


_loop_singleton: AgentLoop | None = None


def get_loop() -> AgentLoop:
    """One AgentLoop per process. ``AgentLoop.db_path`` is resolved
    lazily from ``HISTORIAN_PATH`` (with a ``HISTORIAN_DB_PATH`` alias)
    on each request, so tests that flip the env var between calls pick
    up the new path without rebuilding the loop.
    """
    global _loop_singleton
    if _loop_singleton is None:
        _loop_singleton = AgentLoop()
    return _loop_singleton


def reset_loop_for_tests() -> None:
    """Drop the cached AgentLoop so the next ``get_loop()`` rebuilds it
    against the current ``config/agent.yaml`` and any env overrides.
    """
    global _loop_singleton
    _loop_singleton = None


@router.post("/chat")
async def chat(req: ChatRequest):
    if _agent_mode() == "mock":
        return await event_stream(stream_mock_events(req.query))
    loop = get_loop()
    return await event_stream(loop.stream_events(req.query, req.run_context))
