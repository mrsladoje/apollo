"""PLAN-C §15 — four refusal pathways must end in REFUSAL."""

from __future__ import annotations

import pytest

from apollo.agent.loop import AgentLoop


@pytest.fixture(scope="module")
def loop(historian_db_path) -> AgentLoop:
    return AgentLoop(db_path=historian_db_path)


@pytest.mark.parametrize(
    "query",
    [
        "What is the weather in Madrid?",            # off-topic
        "Did component microwave fail?",             # unknown component
        "What was the heater health in run-9999?",   # unknown run
        "Show me the binder viscosity timeline.",    # no such metric
    ],
)
def test_refusal_pathways(loop: AgentLoop, query: str) -> None:
    response = loop.answer(query)
    assert response.severity == "REFUSAL", query
    assert response.citations == [], query
    assert response.text.startswith("REFUSAL"), query
