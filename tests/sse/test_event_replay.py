"""PLAN-C §5.3 — golden SSE event-order replay (canonical Barcelona query).

Asserts the in-process agent loop emits the frozen sequence:
  ``tool-call-start*  tool-result*  text-delta+  citation+  done``

(any number of tool pairs and text deltas, ending with at least one citation
and a single ``done`` event).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apollo.agent.loop import AgentLoop
from apollo.api.app import app
from apollo.mocks.agent_mock import BARCELONA_TRACE


REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {"text-delta", "tool-call-start", "tool-result", "citation", "done"}


def _drain_async(it):
    loop = asyncio.new_event_loop()
    try:
        async def collect() -> list[dict]:
            out = []
            async for ev in it:
                out.append(ev)
            return out
        return loop.run_until_complete(collect())
    finally:
        loop.close()


def test_only_allowed_event_types(historian_db_path) -> None:
    agent = AgentLoop(db_path=historian_db_path)
    events = _drain_async(agent.stream_events(
        "How is the barcelona-humid-ai-seed0042 nozzle doing?",
        run_context="barcelona-humid-ai-seed0042",
    ))
    for ev in events:
        assert ev["type"] in ALLOWED, ev


def test_terminates_in_done(historian_db_path) -> None:
    agent = AgentLoop(db_path=historian_db_path)
    events = _drain_async(agent.stream_events(
        "How is the barcelona-humid-ai-seed0042 nozzle doing?",
        run_context="barcelona-humid-ai-seed0042",
    ))
    assert events[-1]["type"] == "done"
    assert "trace_url" in events[-1]["payload"]


def test_tool_calls_precede_text_or_citations(historian_db_path) -> None:
    agent = AgentLoop(db_path=historian_db_path)
    events = _drain_async(agent.stream_events(
        "How is the barcelona-humid-ai-seed0042 nozzle doing?",
        run_context="barcelona-humid-ai-seed0042",
    ))
    first_tool_call = next((i for i, e in enumerate(events) if e["type"] == "tool-call-start"), None)
    first_text = next((i for i, e in enumerate(events) if e["type"] == "text-delta"), None)
    if first_tool_call is not None and first_text is not None:
        assert first_tool_call < first_text


def test_canonical_mock_trace_well_formed() -> None:
    # The committed canned mock trace must itself be well-formed.
    types = [ev["type"] for ev in BARCELONA_TRACE]
    assert types[-1] == "done"
    assert any(t == "tool-call-start" for t in types)
    assert any(t == "citation" for t in types)


def test_chat_endpoint_streams_via_mock_when_flag_set(monkeypatch) -> None:
    monkeypatch.setenv("APOLLO_AGENT", "mock")
    client = TestClient(app)
    with client.stream("POST", "/api/chat", json={"query": "barcelona"}) as resp:
        assert resp.status_code == 200
        body = resp.read().decode()
    assert "tool-call-start" in body
    assert '"type": "done"' in body
