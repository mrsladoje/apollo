"""Coverage gates for the public façade and mock backends.

These backends are part of the §3.2 published language (Plan C imports
``sim.api``) and the §4 Step-0 deliverable (``sim.mocks.*``). They must
match the real backends' shape so the swap stays transparent.
"""

from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta

import pytest

from engine.contracts import ComponentId


@pytest.fixture
def fresh_api():
    """Re-import sim.api after env mutation so the env-driven switch fires."""
    import sim.api as api

    yield api
    # Restore default mock-friendly state for downstream tests.
    importlib.reload(api)


def test_api_exports_canonical_surface(fresh_api):
    api = fresh_api
    for name in (
        "query_historian",
        "compare_runs",
        "run_counterfactual",
        "late_interaction_search",
        "HistorianRow",
        "CounterfactualResult",
        "RetrievedRow",
    ):
        assert hasattr(api, name), f"sim.api missing {name!r}"


def test_api_mock_historian_backend(monkeypatch):
    monkeypatch.setenv("HISTORIAN_BACKEND", "mock")
    monkeypatch.setenv("RETRIEVAL_BACKEND", "mock")
    import sim.api as api
    importlib.reload(api)
    rows = api.query_historian("barcelona-humid-none-seed0042")
    assert rows
    metrics = api.compare_runs(["barcelona-humid-none-seed0042"], "uptime_hours")
    assert "barcelona-humid-none-seed0042" in metrics


def test_api_dense_retrieval_backend(monkeypatch, tmp_path):
    from sim.config import SimulationConfig
    from sim.loop import run_simulation

    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="none",
        seed=1,
        horizon_minutes=20,
        historian_path=str(db_path),
    )
    run_simulation(cfg)

    monkeypatch.setenv("HISTORIAN_BACKEND", "real")
    monkeypatch.setenv("RETRIEVAL_BACKEND", "dense")
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    from sim.retrieval.dense_fallback import reset_index
    reset_index()
    import sim.api as api
    importlib.reload(api)

    rows = api.late_interaction_search("nozzle health", top_k=3)
    assert rows
    assert all(isinstance(r.component, ComponentId) for r in rows)


def test_api_lateon_requires_index(monkeypatch):
    """Default LateOn retrieval should fail loudly if the index is missing."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "lateon")
    monkeypatch.setenv("LATEON_INDEX_PATH", "/nonexistent/lateon.index")
    monkeypatch.setenv("HISTORIAN_BACKEND", "mock")
    import sim.api as api
    importlib.reload(api)
    assert callable(api.late_interaction_search)
    with pytest.raises(Exception):
        api.late_interaction_search("thermal cascade", top_k=1)


def test_mock_historian_compare_runs_supports_all_metrics():
    from sim.mocks.historian_mock import compare_runs
    run_id = "stressed-fixed-seed0042"
    for metric in ("uptime_hours", "failure_count", "maintenance_count", "avg_health"):
        out = compare_runs([run_id], metric)
        assert run_id in out
        assert isinstance(out[run_id], float)


def test_mock_historian_rejects_unknown_metric():
    from sim.mocks.historian_mock import compare_runs
    with pytest.raises(ValueError):
        compare_runs(["any"], "not-a-metric")


def test_mock_historian_query_filters():
    from sim.mocks.historian_mock import query_historian
    run_id = "barcelona-humid-none-seed0042"
    all_rows = query_historian(run_id)
    nozzle_rows = query_historian(run_id, ComponentId.NOZZLE)
    assert len(nozzle_rows) < len(all_rows)
    assert all(r.component_id == ComponentId.NOZZLE for r in nozzle_rows)

    base = datetime(2026, 4, 25, 8, 0, 0)
    bounded = query_historian(
        run_id, None, (base + timedelta(minutes=10), base + timedelta(minutes=20))
    )
    assert all(base + timedelta(minutes=10) <= r.t <= base + timedelta(minutes=20) for r in bounded)


def test_mock_counterfactual_returns_typed_result():
    from sim.mocks.counterfactual_mock import run_counterfactual
    base = datetime(2026, 4, 25, 8, 0, 0)
    res = run_counterfactual(
        "stressed-none-seed0042",
        base + timedelta(minutes=120),
        {"action": "MAINTENANCE", "component_id": "blade"},
    )
    assert res.original
    assert res.alternate
    assert {"uptime_delta", "failures_avoided", "cost_delta"} <= set(res.diff)


def test_config_from_run_params_loads_yaml(tmp_path, monkeypatch):
    from sim.config import SimulationConfig

    yaml_path = tmp_path / "policies.yaml"
    yaml_path.write_text(
        "ai_policy:\n"
        "  thresholds:\n"
        "    blade: 0.5\n    motor: 0.5\n    nozzle: 0.5\n"
        "    resistor: 0.5\n    heater: 0.5\n    insulation: 0.5\n"
        "  lookahead_coef: 0.42\n"
    )
    cfg = SimulationConfig.from_run_params(
        "stressed", "ai", 7, yaml_path=str(yaml_path)
    )
    assert cfg.lookahead_coef == 0.42
    assert cfg.thresholds[ComponentId.BLADE] == 0.5


def test_config_from_run_params_no_yaml_for_non_ai(tmp_path):
    from sim.config import SimulationConfig
    cfg = SimulationConfig.from_run_params(
        "stressed", "fixed", 7, yaml_path=str(tmp_path / "missing.yaml")
    )
    assert cfg.thresholds is None
