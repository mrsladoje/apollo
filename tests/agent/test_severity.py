"""PLAN-C §3.2 / FR-3.4 — severity tag present on every response."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apollo.agent.contracts import ApolloResponse, Citation
from apollo.agent.loop import AgentLoop
from engine.contracts import ComponentId

from datetime import datetime


def test_severity_is_one_of_the_four(historian_db_path) -> None:
    loop = AgentLoop(db_path=historian_db_path)
    valid = {"INFO", "WARNING", "CRITICAL", "REFUSAL"}
    for q in [
        "How is the barcelona-humid-ai-seed0042 nozzle?",
        "What is the weather in Madrid?",
    ]:
        resp = loop.answer(q)
        assert resp.severity in valid


def test_severity_outside_set_rejected() -> None:
    with pytest.raises(ValidationError):
        ApolloResponse(severity="HAPPY", text="x", citations=[])  # type: ignore[arg-type]
