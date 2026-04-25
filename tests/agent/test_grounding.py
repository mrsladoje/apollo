"""PLAN-C §6.5 — grounding rules: ≥1 tool call before any non-trivial reply.

This test exercises the canonical Barcelona query through the in-process
``AgentLoop`` and asserts the audit trail contains a tool call.
"""

from __future__ import annotations

from apollo.agent.loop import AgentLoop


def test_canonical_barcelona_calls_at_least_one_tool(historian_db_path) -> None:
    loop = AgentLoop(db_path=historian_db_path)
    response = loop.answer(
        "How is the barcelona-humid-ai-seed0042 nozzle doing?",
        run_context="barcelona-humid-ai-seed0042",
    )
    assert len(response.tool_calls) >= 1
    assert response.tool_calls[0].tool in {
        "query_historian", "late_interaction_search", "compare_runs",
    }
    # Non-REFUSAL responses must carry citations.
    if response.severity != "REFUSAL":
        assert len(response.citations) >= 1


def test_max_tool_calls_per_turn_respected(historian_db_path) -> None:
    loop = AgentLoop(db_path=historian_db_path, max_tool_calls=3)
    response = loop.answer(
        "Compare the barcelona-humid-ai-seed0042 cascade across components",
        run_context="barcelona-humid-ai-seed0042",
    )
    assert len(response.tool_calls) <= 3 + 2  # +2 for deep-investigation cue
