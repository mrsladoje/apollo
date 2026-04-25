"""Mock Apollo agent — returns canned ApolloResponse payloads and deterministic
SSE event streams for the canonical demo queries (ADR-008, PLAN-C §4.1)."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import AsyncIterator

# Canonical demo SSE traces — one per named scenario
BARCELONA_TRACE = [
    {"type": "tool-call-start", "payload": {"tool": "query_historian", "args": {"run_id": "barcelona-01", "component": "nozzle", "time_range": [0, 60]}, "call_id": "tc-001"}},
    {"type": "tool-result", "payload": {"call_id": "tc-001", "result": {"rows": 12, "min_health": 0.31, "max_health": 0.78}}},
    {"type": "tool-call-start", "payload": {"tool": "late_interaction_search", "args": {"query": "nozzle clog cascade", "run_id": "barcelona-01"}, "call_id": "tc-002"}},
    {"type": "tool-result", "payload": {"call_id": "tc-002", "result": {"rows": 4, "top_score": 0.92}}},
    {"type": "text-delta", "payload": {"token": "My "}},
    {"type": "text-delta", "payload": {"token": "nozzle "}},
    {"type": "text-delta", "payload": {"token": "health "}},
    {"type": "text-delta", "payload": {"token": "degraded "}},
    {"type": "text-delta", "payload": {"token": "from 78% "}},
    {"type": "text-delta", "payload": {"token": "to 31% "}},
    {"type": "text-delta", "payload": {"token": "over 60 minutes, "}},
    {"type": "text-delta", "payload": {"token": "triggering a cascade "}},
    {"type": "text-delta", "payload": {"token": "through the resistor "}},
    {"type": "text-delta", "payload": {"token": "thermal path."}},
    {"type": "citation", "payload": {"run_id": "barcelona-01", "component": "nozzle", "timestamp": "2026-04-25T10:00:00Z"}},
    {"type": "citation", "payload": {"run_id": "barcelona-01", "component": "resistor", "timestamp": "2026-04-25T10:45:00Z"}},
    {"type": "done", "payload": {"trace_url": "https://cloud.langfuse.com/trace/barcelona-01-mock"}},
]

PHOENIX_TRACE = [
    {"type": "tool-call-start", "payload": {"tool": "query_historian", "args": {"run_id": "phoenix-02", "component": "heater", "time_range": [0, 48]}, "call_id": "tc-010"}},
    {"type": "tool-result", "payload": {"call_id": "tc-010", "result": {"rows": 8, "min_health": 0.42, "max_health": 0.95}}},
    {"type": "text-delta", "payload": {"token": "My "}},
    {"type": "text-delta", "payload": {"token": "heater "}},
    {"type": "text-delta", "payload": {"token": "maintained "}},
    {"type": "text-delta", "payload": {"token": "nominal efficiency "}},
    {"type": "text-delta", "payload": {"token": "for 48 hours "}},
    {"type": "text-delta", "payload": {"token": "despite thermal cycling stress."}},
    {"type": "citation", "payload": {"run_id": "phoenix-02", "component": "heater", "timestamp": "2026-04-25T08:00:00Z"}},
    {"type": "done", "payload": {"trace_url": "https://cloud.langfuse.com/trace/phoenix-02-mock"}},
]

REFUSAL_TRACE = [
    {"type": "text-delta", "payload": {"token": "REFUSAL — "}},
    {"type": "text-delta", "payload": {"token": "I cannot answer that "}},
    {"type": "text-delta", "payload": {"token": "from the data I have. "}},
    {"type": "text-delta", "payload": {"token": "The historian returned no rows "}},
    {"type": "text-delta", "payload": {"token": "matching that query. "}},
    {"type": "text-delta", "payload": {"token": "I will not guess."}},
    {"type": "done", "payload": {"trace_url": "https://cloud.langfuse.com/trace/refusal-mock"}},
]

OFF_TOPIC_KEYWORDS = {"weather", "madrid", "microwave", "binder", "run-9999"}


def _select_trace(query: str) -> list[dict]:
    q = query.lower()
    if any(kw in q for kw in OFF_TOPIC_KEYWORDS):
        return REFUSAL_TRACE
    if "barcelona" in q or "nozzle" in q:
        return BARCELONA_TRACE
    if "phoenix" in q or "heater" in q:
        return PHOENIX_TRACE
    return BARCELONA_TRACE  # default canonical path


async def stream_mock_events(query: str) -> AsyncIterator[dict]:
    """Yield SSE event dicts with realistic ~80 ms inter-event delay."""
    trace = _select_trace(query)
    for event in trace:
        await asyncio.sleep(0.08)
        yield event
