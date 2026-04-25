import hashlib
import sqlite3

from sim.config import SimulationConfig
from sim.loop import run_simulation


def _dump_component_states(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT run_id, t, component_id, health, status, metrics_json
           FROM component_states
           ORDER BY run_id, t, component_id"""
    ).fetchall()
    return repr(rows).encode()


def test_loop_persists_every_tick_component_driver_and_forecast(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="barcelona-humid",
        policy="none",
        seed=7,
        horizon_minutes=30,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM drivers WHERE run_id = ?", (run_id,)).fetchone()[0] == 30
    assert conn.execute("SELECT count(*) FROM component_states WHERE run_id = ?", (run_id,)).fetchone()[0] == 180
    assert conn.execute("SELECT count(*) FROM forecasts WHERE run_id = ?", (run_id,)).fetchone()[0] == 180


def test_repeated_run_is_byte_identical_for_component_states(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="phoenix-dry",
        policy="none",
        seed=11,
        horizon_minutes=60,
        historian_path=str(db_path),
    )

    run_simulation(cfg)
    first = hashlib.sha256(_dump_component_states(db_path)).hexdigest()
    run_simulation(cfg)
    second = hashlib.sha256(_dump_component_states(db_path)).hexdigest()

    assert first == second

