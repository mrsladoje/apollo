from datetime import datetime, timedelta

from engine.contracts import ComponentId
from sim.config import SimulationConfig
from sim.historian.connection import connect
from sim.historian.reader import compare_runs, query_historian
from sim.loop import run_simulation


def test_schema_tables_and_wal(tmp_path):
    db_path = tmp_path / "historian.db"
    conn = connect(str(db_path))

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {
        "runs",
        "drivers",
        "component_states",
        "maintenance_events",
        "obituaries",
        "forecasts",
        "checkpoints",
    }.issubset(tables)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_query_historian_and_compare_runs(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="fixed",
        seed=42,
        horizon_minutes=120,
        historian_path=str(db_path),
    )
    run_id = run_simulation(cfg)

    rows = query_historian(
        run_id,
        ComponentId.NOZZLE,
        (datetime(2026, 4, 25, 8, 0, 0), datetime(2026, 4, 25, 9, 59, 0)),
        db_path=str(db_path),
    )
    assert len(rows) == 120
    assert rows[0].component_id is ComponentId.NOZZLE

    metrics = compare_runs([run_id], "maintenance_count", db_path=str(db_path))
    assert metrics[run_id] >= 1.0

