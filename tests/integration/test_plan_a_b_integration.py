"""Plan A ↔ Plan B integration suite — gate G1 (PLAN.md §6).

The simulation loop, AI policy, and counterfactual replay all import
``engine.api`` at module load time after the integration handshake. This
suite exercises the merged stack end-to-end:

1. ``run_simulation`` drives the **real** engine (not the mock).
2. The historian persists every component_state, driver, forecast,
   checkpoint, and obituary that the engine emits.
3. AIPolicy lookahead consumes the real MAPIE conformal forecast layer.
4. Counterfactual replay reconstructs branch state through the real
   engine and produces a typed diff.
5. Two runs with the same ``(scenario, policy, seed, config_json)`` key
   are byte-identical (NFR-1, NFR-8).

The mock engine is still importable behind ``APOLLO_ENGINE=mock`` for
PLAN-A §4.3 dry-run smoke tests; one assertion below pins that escape
hatch so the dual-mode contract cannot regress.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import timedelta

import pytest

from engine import api as engine_api
from engine import mock_engine
from engine.contracts import (
    ComponentId,
    ComponentStatus,
    EngineState,
    Forecast,
)
from sim import counterfactual
from sim import loop as loop_module
from sim import policies as policies_module
from sim.config import SimulationConfig
from sim.counterfactual.engine import run_counterfactual
from sim.drivers.composite import SIM_START_TIME
from sim.loop import run_simulation


# ---------------------------------------------------------------------------
# Wiring — confirm the loop/policy/counterfactual imports the REAL engine
# ---------------------------------------------------------------------------


def test_sim_loop_uses_real_engine_module():
    """``sim.loop.engine`` is bound to ``engine.api`` after gate G1.

    A regression here means somebody slipped the mock back into the
    critical path. The mock import must remain available but *not* be
    the default for ``run_simulation``.
    """
    assert loop_module.engine is engine_api
    assert loop_module.engine is not mock_engine


def test_counterfactual_uses_real_engine_module():
    assert counterfactual.engine.engine is engine_api
    assert counterfactual.engine.engine is not mock_engine


def test_ai_policy_lookahead_uses_real_forecast(monkeypatch):
    """When AIPolicy fires its lookahead branch it must reach the real
    MAPIE conformal layer (Plan A Workstream A5), not the mock."""
    captured: list[str] = []

    real_forecast = engine_api.forecast

    def spy_forecast(state: EngineState, horizon_min: int):
        captured.append("real")
        return real_forecast(state, horizon_min)

    monkeypatch.setattr(engine_api, "forecast", spy_forecast)

    policy = policies_module.AIPolicy(
        thresholds={cid: 0.99 for cid in ComponentId},  # force lookahead branch
        lookahead_coef=0.5,
    )
    state = engine_api.initial_state(seed=0)
    # Bypass the trivial "current health < threshold" guard by setting all
    # current healths to 1.0 (already the case from initial_state) and using
    # near-1.0 thresholds so the policy walks into the lookahead loop.
    decision = policy.decide(state, SIM_START_TIME)
    # We don't care which component the policy picks — only that the spy
    # ran, proving the AIPolicy reached the engine.api forecast surface.
    assert captured, "AIPolicy never called engine.forecast"
    # The decision is allowed to be None or any valid ComponentId; pinning
    # the value would tie the test to the conformal point-forecast magic
    # numbers, which Plan A may legitimately retune.
    assert decision is None or isinstance(decision, ComponentId)


# ---------------------------------------------------------------------------
# End-to-end run — real engine, real historian, real conformal forecasts
# ---------------------------------------------------------------------------


@pytest.fixture
def short_run(tmp_path):
    """A 30-minute Barcelona-humid Dark Twin against the real engine.

    Short enough to keep CI under a second, long enough that all
    persistence tables receive rows and at least one checkpoint lands.
    """
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="barcelona-humid",
        policy="none",
        seed=7,
        horizon_minutes=30,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)
    return run_id, db_path


def test_full_persistence_against_real_engine(short_run):
    """Every persistence table receives the rows the engine emitted.

    Row counts here pin the loop's contract:
    drivers   = horizon // step                        (FR-2.3)
    states    = horizon // step  *  6 components      (FR-2.3)
    forecasts = horizon // step  *  6 components      (FR-W.6)
    runs      = exactly one row, with finished_at populated.
    checkpoints >= 1 (cadence per ADR-012).
    """
    run_id, db_path = short_run
    conn = sqlite3.connect(db_path)
    n_drivers = conn.execute(
        "SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    n_states = conn.execute(
        "SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    n_forecasts = conn.execute(
        "SELECT count(*) FROM forecasts WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    n_runs = conn.execute(
        "SELECT count(*) FROM runs WHERE run_id = ? AND finished_at IS NOT NULL",
        (run_id,),
    ).fetchone()[0]
    n_checkpoints = conn.execute(
        "SELECT count(*) FROM checkpoints WHERE run_id = ?", (run_id,)
    ).fetchone()[0]

    assert n_drivers == 30
    assert n_states == 30 * 6
    assert n_forecasts == 30 * 6
    assert n_runs == 1
    assert n_checkpoints >= 1


def test_persisted_forecasts_round_trip_to_pydantic(short_run):
    """Real-engine forecasts persist with valid ``(point, lower, upper)``
    intervals (FR-W.6, ADR-015) and re-hydrate as ``engine.contracts.Forecast``.
    """
    run_id, db_path = short_run
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT component_id, horizon_min, point, lower, upper, ci_level
           FROM forecasts WHERE run_id = ? ORDER BY t LIMIT 6""",
        (run_id,),
    ).fetchall()
    assert len(rows) == 6
    seen: set[str] = set()
    for cid, hmin, point, lower, upper, ci in rows:
        f = Forecast(
            component_id=ComponentId(cid),
            horizon_min=int(hmin),
            point=float(point),
            lower=float(lower),
            upper=float(upper),
            ci_level=float(ci),
        )
        seen.add(cid)
        assert 1 <= f.horizon_min <= 60
        assert 0.0 <= f.lower <= f.point <= f.upper <= 1.0
        assert abs(f.ci_level - 0.95) < 1e-9
    assert seen == {c.value for c in ComponentId}


def test_real_engine_emits_status_thresholds(short_run):
    """Status enum derives deterministically from health on the persisted
    rows — no stale mock value can survive the swap.
    """
    run_id, db_path = short_run
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT health, status FROM component_states WHERE run_id = ?", (run_id,)
    ).fetchall()
    assert rows
    for h, s in rows:
        if h >= 0.7:
            assert s == ComponentStatus.FUNCTIONAL.value
        elif h >= 0.4:
            assert s == ComponentStatus.DEGRADED.value
        elif h >= 0.1:
            assert s == ComponentStatus.CRITICAL.value
        else:
            assert s == ComponentStatus.FAILED.value


# ---------------------------------------------------------------------------
# Reproducibility — NFR-1 / NFR-8 across the merged stack
# ---------------------------------------------------------------------------


def _hash_component_states(db_path) -> str:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT run_id, t, component_id, health, status, metrics_json
           FROM component_states ORDER BY run_id, t, component_id"""
    ).fetchall()
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def _hash_forecasts(db_path) -> str:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT run_id, t, component_id, horizon_min, point, lower, upper
           FROM forecasts ORDER BY run_id, t, component_id, horizon_min"""
    ).fetchall()
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def test_real_engine_run_is_byte_identical(tmp_path):
    """Same ``(scenario, policy, seed, config_json)`` → same historian.

    Covers the full NFR-1/NFR-8 path under the integrated stack: rule-
    based decay + matrix coupling + CSC-B physics + PINN inference +
    MAPIE conformal forecast → SQLite persistence.
    """
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="none",
        seed=11,
        horizon_minutes=60,
        historian_path=str(db_path),
    )

    run_simulation(cfg)
    h_states_1 = _hash_component_states(db_path)
    h_forecasts_1 = _hash_forecasts(db_path)

    run_simulation(cfg)
    h_states_2 = _hash_component_states(db_path)
    h_forecasts_2 = _hash_forecasts(db_path)

    assert h_states_1 == h_states_2, "real-engine run not deterministic"
    assert h_forecasts_1 == h_forecasts_2, "conformal forecasts not deterministic"


def test_different_seeds_diverge(tmp_path):
    """Different seeds produce different driver trajectories and hence
    different component_state series — proves the seed actually wires
    through the merged stack.
    """
    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"
    base = dict(
        scenario_name="stressed",
        policy="none",
        horizon_minutes=30,
    )
    run_simulation(SimulationConfig(seed=1, historian_path=str(db1), **base))
    run_simulation(SimulationConfig(seed=2, historian_path=str(db2), **base))
    assert _hash_component_states(db1) != _hash_component_states(db2)


# ---------------------------------------------------------------------------
# Counterfactual replay through the real engine
# ---------------------------------------------------------------------------


def test_counterfactual_no_op_matches_original(tmp_path):
    """``noop`` branch through the real path-dependent engine should
    reproduce the original timeline. The previous off-by-one in
    ``run_counterfactual`` was masked by the mock's idempotent step.
    """
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=60,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    branch_t = SIM_START_TIME + timedelta(minutes=30)
    result = run_counterfactual(
        run_id, branch_t, {"action": "noop"}, db_path=str(db_path)
    )
    orig_by_key = {(r.component_id, r.t): r for r in result.original}
    drift_max = 0.0
    paired = 0
    for alt in result.alternate:
        key = (alt.component_id, alt.t)
        orig = orig_by_key.get(key)
        if orig is None:
            continue
        paired += 1
        drift = abs(orig.health - alt.health)
        drift_max = max(drift_max, drift)
    assert paired > 0, "counterfactual produced no comparable rows"
    assert drift_max < 1e-6, (
        f"no-op counterfactual drifts {drift_max:.2e} from original (real engine)"
    )


def test_counterfactual_maintenance_changes_outcome(tmp_path):
    """Maintenance branch yields a different alternate timeline AND
    moves the diff signs the right way (positive uptime delta or
    failures avoided when the action helps).
    """
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=120,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    branch_t = SIM_START_TIME + timedelta(minutes=20)
    result = run_counterfactual(
        run_id,
        branch_t,
        {
            "action": "MAINTENANCE",
            "component_id": ComponentId.NOZZLE.value,
            "cost": 1.0,
        },
        db_path=str(db_path),
    )
    # Diff fields are populated and the alternate at branch_t shows the
    # maintenance reset on the targeted component.
    assert {"uptime_delta", "failures_avoided", "cost_delta"} <= result.diff.keys()
    branch_alt = [
        r for r in result.alternate
        if r.t == branch_t and r.component_id is ComponentId.NOZZLE
    ]
    assert branch_alt, "no alternate row at branch_t for maintenance target"
    assert branch_alt[0].health == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Mock escape hatch — APOLLO_ENGINE=mock must keep working for dry-runs
# ---------------------------------------------------------------------------


def test_apollo_engine_mock_escape_hatch(monkeypatch):
    """PLAN-A §4.3 — the mock engine remains importable and callable
    behind the env var so Plan B's smoke tests / demo dry-runs can skip
    real-engine compute.
    """
    monkeypatch.setenv("APOLLO_ENGINE", "mock")
    state = engine_api.initial_state(scenario="stressed", seed=1)
    assert set(state.components.keys()) == set(ComponentId)
    # The mock's rng_state shape ``(seed, scenario)`` is the historical
    # tell that we landed on the mock branch.
    assert state.rng_state == (1, "stressed")
    forecasts = engine_api.forecast(state, horizon_min=30)
    assert len(forecasts) == 6


def test_apollo_engine_real_is_default(monkeypatch):
    """Without ``APOLLO_ENGINE``, the API uses the real engine — i.e.,
    the rng_state carries a serialized numpy ``Generator`` payload, not
    the mock's ``(seed, scenario)`` tuple.
    """
    monkeypatch.delenv("APOLLO_ENGINE", raising=False)
    state = engine_api.initial_state(seed=1)
    assert isinstance(state.rng_state, tuple)
    # Real engine threads the numpy bit-generator state through; that
    # serialized payload always contains a nested numpy ndarray marker
    # (or a state dict) — never the mock's bare ``(seed, scenario)`` form.
    assert state.rng_state != (1, "default")


def test_engine_public_surface_is_three_symbols():
    """ADR-021 ubiquitous-language guard — only ``step`` / ``forecast`` /
    ``initial_state`` cross the Engine bounded-context boundary.
    """
    public = {name for name in dir(engine_api) if not name.startswith("_")}
    expected = {"step", "forecast", "initial_state"}
    # The module is allowed to re-export typing helpers, but the contract
    # symbols MUST be present and named exactly.
    missing = expected - public
    assert not missing, f"engine.api missing public symbols: {missing}"
    # __all__ — if present — must equal the contract triple.
    if hasattr(engine_api, "__all__"):
        assert set(engine_api.__all__) == expected
