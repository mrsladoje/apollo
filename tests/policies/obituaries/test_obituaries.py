"""FR-W.4 / §11 — obituary generation, voice, and citation resolvability.

Runs a NONE Dark Twin to horizon end so the heater (FAILED ~t=480) and
nozzle (FAILED ~t=520) generate obituaries. Then asserts the four §11.8
acceptance properties:

1. ≥ 1 obituary in every NONE run.
2. Narrative passes ADR-019 voice lint (no `!`, no first-person, no banned
   adjectives).
3. Every citation resolves to a live ``component_states`` row.
4. Generation latency stays under the 5-second SLA on M3 hardware.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timedelta

import pytest

from sim.analytics.obituary import _BANNED_TOKENS, _FIRST_PERSON, generate_obituary
from sim.config import SimulationConfig
from sim.loop import run_simulation


def _setup_run(tmp_path, horizon=600):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=horizon,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)
    return run_id, db_path


def test_obituary_generated_for_every_dark_twin_failure(tmp_path):
    run_id, db_path = _setup_run(tmp_path)
    conn = sqlite3.connect(db_path)
    obit_count = conn.execute(
        "SELECT count(*) FROM obituaries WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert obit_count >= 1


def test_obituary_voice_constraints(tmp_path):
    run_id, db_path = _setup_run(tmp_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT narrative FROM obituaries WHERE run_id = ?", (run_id,)
    ).fetchall()
    assert rows
    for (narrative,) in rows:
        assert "!" not in narrative
        assert _FIRST_PERSON.search(narrative) is None
        lower = narrative.lower()
        for tok in _BANNED_TOKENS:
            assert tok not in lower, f"banned token {tok!r} in: {narrative!r}"


def test_every_citation_is_resolvable(tmp_path):
    run_id, db_path = _setup_run(tmp_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT citations_json FROM obituaries WHERE run_id = ?", (run_id,)
    ).fetchall()
    assert rows
    for (cit_json,) in rows:
        citations = json.loads(cit_json)
        for c in citations:
            t_iso = c["t"]
            comp = c["component"]
            # The citation's component_states row must exist.
            row = conn.execute(
                """SELECT 1 FROM component_states
                   WHERE run_id = ? AND component_id = ? AND t = ?""",
                (c["run_id"], comp, t_iso),
            ).fetchone()
            assert row is not None, f"unresolvable citation {c}"


def test_obituary_latency_under_5s(tmp_path):
    """§11.6 — synchronous generation must stay under 5 s.

    We re-run a single ``generate_obituary`` after the simulation populates
    history, so the timing is bounded by the per-call cost (not the whole
    sim).
    """
    run_id, db_path = _setup_run(tmp_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT failure_t, component_id FROM obituaries
           WHERE run_id = ? LIMIT 1""",
        (run_id,),
    ).fetchall()
    assert rows
    failure_t, comp_id = rows[0]
    failure_dt = datetime.fromisoformat(failure_t)

    from engine.contracts import (
        ComponentId,
        ComponentState,
        ComponentStatus,
        EngineState,
    )

    # Build a trivial state shim — we only need ``state.components[cid].health``.
    state = EngineState(
        components={
            cid: ComponentState(
                component_id=cid,
                health=0.05,
                status=ComponentStatus.FAILED,
                metrics={},
            )
            for cid in ComponentId
        },
        coupling_matrix=[[0.0] * 6 for _ in range(6)],
        rng_state=(0, run_id),
        events=(),
    )

    t0 = time.perf_counter()
    obit = generate_obituary(
        run_id, ComponentId(comp_id), failure_dt, state, db_path=str(db_path)
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"obituary latency {elapsed:.3f}s exceeds 5 s SLA"
    assert obit["narrative"]
