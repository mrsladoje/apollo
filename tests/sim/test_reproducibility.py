"""FR-2.7 / NFR-8 — same ``(scenario, policy, seed, config_json)`` ⇒
byte-identical historian.

The §16 gate hashes the SHA-256 of the ``component_states`` table dump
across two builds and asserts no diff. We mirror that here at small scale
so the property is checked on every CI run instead of only when
``make build_grid`` is invoked.
"""

from __future__ import annotations

import hashlib
import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def _table_sha256(db_path: str, table: str) -> str:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    conn.close()
    h = hashlib.sha256()
    h.update(repr(rows).encode())
    return h.hexdigest()


def _run(tmp_path, scenario, policy, seed, **kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / f"{scenario}-{policy}-{seed}.db"
    cfg = SimulationConfig(
        scenario_name=scenario,
        policy=policy,
        seed=seed,
        horizon_minutes=kwargs.pop("horizon_minutes", 90),
        historian_path=str(db_path),
        **kwargs,
    )
    run_simulation(cfg)
    return str(db_path)


def test_component_states_hash_stable_across_runs(tmp_path):
    a = _run(tmp_path / "a", "stressed", "fixed", 42)
    b = _run(tmp_path / "b", "stressed", "fixed", 42)
    assert _table_sha256(a, "component_states") == _table_sha256(b, "component_states")


def test_drivers_hash_stable_across_runs(tmp_path):
    a = _run(tmp_path / "a", "phoenix-dry", "none", 7)
    b = _run(tmp_path / "b", "phoenix-dry", "none", 7)
    assert _table_sha256(a, "drivers") == _table_sha256(b, "drivers")


def test_different_seeds_produce_different_drivers(tmp_path):
    a = _run(tmp_path / "a", "barcelona-humid", "none", 1)
    b = _run(tmp_path / "b", "barcelona-humid", "none", 2)
    assert _table_sha256(a, "drivers") != _table_sha256(b, "drivers")
