"""Regression: failures landing on a throttle-skipped historian tick must
still reach the SSE stream (otherwise the chart marker and the obit-card
"Failure log" silently lose entries).
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from apollo.api.routes.sim import _historian_events


SCHEMA = Path("src/sim/historian/schema.sql").read_text()


def _seed_db(db_path: Path, *, run_id: str, fail_tick_index: int) -> str:
    """Build a tiny historian: 5 ticks, one component, obituary on
    ``fail_tick_index``. Returns the ISO timestamp of that tick.
    """
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)

    base = datetime(2026, 4, 25, 8, 0, 0)
    timestamps = [(base + timedelta(minutes=i)).isoformat() for i in range(5)]

    conn.execute(
        "INSERT INTO runs (run_id, scenario_name, policy, started_at, seed, config_json) "
        "VALUES (?, 'barcelona-humid', 'none', ?, 0, '{}')",
        (run_id, timestamps[0]),
    )
    for i, t_iso in enumerate(timestamps):
        conn.execute(
            "INSERT INTO component_states (run_id, t, component_id, health, status, metrics_json) "
            "VALUES (?, ?, 'heater', ?, ?, '{}')",
            (run_id, t_iso, max(0.0, 1.0 - 0.25 * i), "FAILED" if i == fail_tick_index else "FUNCTIONAL"),
        )
    conn.execute(
        "INSERT INTO obituaries (run_id, component_id, failure_t, narrative, citations_json) "
        "VALUES (?, 'heater', ?, 'heater died', '[]')",
        (run_id, timestamps[fail_tick_index]),
    )
    conn.commit()
    conn.close()
    return timestamps[fail_tick_index]


def _drain(conn: sqlite3.Connection, run_id: str, every_n_ticks: int) -> list[dict]:
    async def collect() -> list[dict]:
        out: list[dict] = []
        async for blob in _historian_events(
            conn,
            run_id,
            "dark-twin",
            delay=0.0,
            every_n_ticks=every_n_ticks,
            speed=1.0,
        ):
            out.append(json.loads(blob))
        return out

    return asyncio.run(collect())


@pytest.mark.parametrize("fail_idx", [0, 1, 2, 3, 4])
def test_failure_emitted_regardless_of_throttle_offset(tmp_path, fail_idx):
    """With ``every_n_ticks=2``, ticks 1 and 3 are throttled out. The
    failure/obituary pair must still be emitted on whichever tick they
    actually land on.
    """
    db = tmp_path / "h.db"
    run_id = f"run-{fail_idx}"
    _seed_db(db, run_id=run_id, fail_tick_index=fail_idx)

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        events = _drain(conn, run_id, every_n_ticks=2)
    finally:
        conn.close()

    failures = [e for e in events if e["type"] == "failure"]
    obits = [e for e in events if e["type"] == "obituary"]

    assert len(failures) == 1, f"expected 1 failure, got {failures}"
    assert len(obits) == 1, f"expected 1 obituary, got {obits}"
    assert failures[0]["component"] == "heater"
    assert failures[0]["t_fail"] == fail_idx
    assert obits[0]["narrative"] == "heater died"


def test_throttle_still_thins_ticks(tmp_path):
    """Sanity check: ``every_n_ticks=2`` still drops half the ticks."""
    db = tmp_path / "h.db"
    run_id = "run-thin"
    _seed_db(db, run_id=run_id, fail_tick_index=4)  # failure on emitted tick

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        events = _drain(conn, run_id, every_n_ticks=2)
    finally:
        conn.close()

    ticks = [e for e in events if e["type"] == "tick"]
    # 5 historian timestamps, every_n_ticks=2 ⇒ indices 0, 2, 4 emitted = 3 ticks.
    assert len(ticks) == 3
