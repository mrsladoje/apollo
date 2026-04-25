"""NFR-4 — late-interaction retrieval p95 < 200 ms over the demo corpus.

The plan calls out 10k rows on M3 CPU. We exercise the same property at
smaller scale here so it gates every CI run; the §16 demo gate runs the
full 9-grid corpus through the same code path. Both the dense fallback
and the mock backend honor the budget; the live LateOn path is exercised
only when ``RETRIEVAL_BACKEND=lateon`` and the index is built.
"""

from __future__ import annotations

import os
import time
from datetime import timedelta

import pytest

from sim.config import SimulationConfig
from sim.drivers.composite import SIM_START_TIME
from sim.loop import run_simulation
from sim.retrieval.dense_fallback import (
    late_interaction_search,
    reset_index,
)


CANONICAL_QUERIES = [
    "nozzle clog escalation",
    "thermal cascade",
    "moment of regret",
    "blade wear",
    "motor bearing temperature",
    "insulation degradation",
    "heater drift",
    "powder contamination CSC-C",
    "humidity spike Barcelona",
    "voltage stability dropout",
] * 10  # 100 queries total


def _build_corpus(tmp_path):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=180,
        historian_path=str(db_path),
    )
    run_simulation(cfg)
    return db_path


def test_dense_fallback_p95_under_200ms(tmp_path, monkeypatch):
    db_path = _build_corpus(tmp_path)
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    reset_index()

    # Warm the index once (build cost is amortized across queries in prod).
    late_interaction_search(CANONICAL_QUERIES[0], top_k=10)

    latencies = []
    for q in CANONICAL_QUERIES:
        t0 = time.perf_counter()
        late_interaction_search(q, top_k=10)
        latencies.append(time.perf_counter() - t0)

    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies)) - 1]
    assert p95 < 0.200, f"p95={p95 * 1000:.1f}ms exceeds NFR-4 budget"


def test_dense_fallback_run_id_filter(tmp_path, monkeypatch):
    db_path = _build_corpus(tmp_path)
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    reset_index()
    rows = late_interaction_search(
        "nozzle clog",
        run_id="stressed-none-seed0042",
        top_k=5,
    )
    assert rows
    assert all(r.run_id == "stressed-none-seed0042" for r in rows)
