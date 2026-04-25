"""Chat route — POST /api/chat returns SSE stream (PLAN-C §5.1)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apollo.api.sse import event_stream
from apollo.mocks.agent_mock import stream_mock_events

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    query: str
    run_context: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest):
    return await event_stream(stream_mock_events(req.query))
