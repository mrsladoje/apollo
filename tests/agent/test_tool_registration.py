"""PLAN-C §6.5 — five tools registered with Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel

from apollo.agent.tools import REGISTRY, list_tools

EXPECTED = {
    "query_historian",
    "late_interaction_search",
    "compare_runs",
    "run_counterfactual",
    "plot_component_history",
}


def test_five_tools_registered() -> None:
    assert set(REGISTRY) == EXPECTED


def test_each_tool_has_pydantic_schema() -> None:
    for name, entry in REGISTRY.items():
        assert issubclass(entry["args_model"], BaseModel), name
        assert callable(entry["call"]), name
        assert entry["schema"].name == name


def test_list_tools_round_trip() -> None:
    schemas = list_tools()
    assert {s.name for s in schemas} == EXPECTED
