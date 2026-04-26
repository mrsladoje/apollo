"""Plan B -> Plan C integration suite — gate G2 guard.

These tests prove Apollo's tool layer and What-If route consume Plan B's
published ``sim.contracts`` surface instead of bypassing it with raw mocks.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from apollo.agent.tools.registry import invoke
from apollo.api.app import app
from engine.contracts import ComponentId
from sim.config import SimulationConfig
from sim.contracts import CounterfactualResult, HistorianRow, RetrievedRow
from sim.drivers.composite import SIM_START_TIME
from sim.loop import run_simulation


def _build_short_run(tmp_path, monkeypatch):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="barcelona-humid",
        policy="none",
        seed=42,
        horizon_minutes=30,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)
    monkeypatch.setenv("HISTORIAN_BACKEND", "real")
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    monkeypatch.setenv("APOLLO_TOOLS_BACKEND", "auto")
    monkeypatch.delenv("USE_MOCKS", raising=False)
    return run_id


def test_apollo_registry_calls_real_plan_b_contracts(tmp_path, monkeypatch):
    run_id = _build_short_run(tmp_path, monkeypatch)
    start = SIM_START_TIME + timedelta(minutes=5)
    end = SIM_START_TIME + timedelta(minutes=15)

    rows = invoke(
        "query_historian",
        {
            "run_id": run_id,
            "component": ComponentId.NOZZLE.value,
            "time_range": (start, end),
        },
    )
    parsed_rows = [HistorianRow.model_validate(row) for row in rows]
    assert parsed_rows
    assert {row.component_id for row in parsed_rows} == {ComponentId.NOZZLE}

    comparison = invoke(
        "compare_runs",
        {"run_ids": [run_id], "metric": "avg_health"},
    )
    assert set(comparison) == {run_id}
    assert 0.0 <= comparison[run_id] <= 1.0

    counterfactual = invoke(
        "run_counterfactual",
        {
            "run_id": run_id,
            "branch_t": SIM_START_TIME + timedelta(minutes=10),
            "alternate_action": {
                "action": "MAINTENANCE",
                "component_id": ComponentId.NOZZLE.value,
            },
        },
    )
    parsed = CounterfactualResult.model_validate(counterfactual)
    assert parsed.original
    assert parsed.alternate
    assert {"uptime_delta", "failures_avoided", "cost_delta"} <= parsed.diff.keys()


def test_whatif_route_projects_real_counterfactual(tmp_path, monkeypatch):
    run_id = _build_short_run(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/whatif",
        json={
            "run_id": run_id,
            "branch_t": 10,
            "alt_action": "clean_nozzle",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["branch_t"] == 10.0
    assert body["original_health"]
    assert body["alt_health"]
    assert {"original", "alternate", "diff"} <= body["counterfactual"].keys()


def test_apollo_mock_tools_still_validate_against_plan_b_contracts(monkeypatch):
    monkeypatch.setenv("APOLLO_TOOLS_BACKEND", "mock")
    monkeypatch.delenv("USE_MOCKS", raising=False)
    start = SIM_START_TIME + timedelta(minutes=10)
    end = SIM_START_TIME + timedelta(minutes=20)

    historian_rows = invoke(
        "query_historian",
        {
            "run_id": "barcelona-01",
            "component": ComponentId.NOZZLE.value,
            "time_range": (start, end),
        },
    )
    assert [HistorianRow.model_validate(row) for row in historian_rows]

    retrieved = invoke(
        "late_interaction_search",
        {"query": "nozzle critical", "run_id": "barcelona-01", "top_k": 3},
    )
    assert [RetrievedRow.model_validate(row) for row in retrieved]

    comparison = invoke(
        "compare_runs",
        {"run_ids": ["barcelona-01"], "metric": "avg_health"},
    )
    assert isinstance(comparison["barcelona-01"], float)

    counterfactual = invoke(
        "run_counterfactual",
        {
            "run_id": "barcelona-01",
            "branch_t": start,
            "alternate_action": {
                "action": "MAINTENANCE",
                "component_id": ComponentId.NOZZLE.value,
            },
        },
    )
    assert CounterfactualResult.model_validate(counterfactual).alternate


def test_use_mocks_umbrella_routes_tools_to_mock_backend(monkeypatch):
    monkeypatch.setenv("USE_MOCKS", "1")
    monkeypatch.setenv("APOLLO_TOOLS_BACKEND", "auto")
    rows = invoke(
        "query_historian",
        {
            "run_id": "barcelona-01",
            "component": ComponentId.BLADE.value,
            "time_range": (
                SIM_START_TIME,
                SIM_START_TIME + timedelta(minutes=5),
            ),
        },
    )
    parsed = [HistorianRow.model_validate(row) for row in rows]
    assert parsed
    assert {row.run_id for row in parsed} == {"barcelona-01"}
