"""§8.3 — ``sim.build_grid`` produces the canonical 9 stable run_ids."""

from __future__ import annotations

import os
import sqlite3

from sim import build_grid as build_grid_mod


def test_build_grid_writes_nine_runs(tmp_path, monkeypatch):
    db_path = tmp_path / "historian.db"
    monkeypatch.chdir(tmp_path)
    # Patch the default historian_path each scenario+policy uses by setting
    # SimulationConfig defaults via env or by writing a small wrapper. Easier:
    # inject through the loop by overriding from_run_params results.
    from sim.config import SimulationConfig
    from sim.loop import run_simulation

    original_from_run_params = SimulationConfig.from_run_params

    def _short_run(scenario_name, policy, seed=42, **kw):
        cfg = original_from_run_params(scenario_name, policy, seed=seed, **kw)
        return cfg.model_copy(update={
            "horizon_minutes": 30,
            "historian_path": str(db_path),
        })

    monkeypatch.setattr(SimulationConfig, "from_run_params", classmethod(
        lambda cls, *a, **kw: _short_run(*a, **kw)
    ))

    build_grid_mod.build_grid()

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT run_id FROM runs").fetchall()
    assert len(rows) == 9
