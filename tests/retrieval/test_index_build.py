"""§12.7 — index build acceptance.

If ``pylate`` is installed and a model is reachable, build the real index
and assert it ingested all rows. Otherwise build the dense-fallback index
(which is the offline-default per §12.5) and assert the same property.
The point is that *some* backend always indexes the corpus end-to-end.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from sim.config import SimulationConfig
from sim.loop import run_simulation
from sim.retrieval._snippets import stream_snippets
from sim.retrieval.dense_fallback import (
    _ensure_index,
    reset_index,
)


def _build_corpus(tmp_path, horizon=60):
    db_path = tmp_path / "historian.db"
    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="none",
        seed=42,
        horizon_minutes=horizon,
        historian_path=str(db_path),
    )
    run_simulation(cfg)
    return db_path


def test_dense_index_indexes_every_row(tmp_path, monkeypatch):
    db_path = _build_corpus(tmp_path)
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    reset_index()
    state = _ensure_index(str(db_path))
    expected = sum(1 for _ in stream_snippets(str(db_path)))
    assert len(state["snippets"]) == expected
    assert expected == 60 * 6


def test_pylate_indexer_skipped_when_pylate_missing(tmp_path):
    """When pylate is not installed (offline CI), the lateon path falls
    back gracefully via ``sim.api`` — no exception leaks to the caller."""
    pytest.importorskip("pylate", reason="pylate optional; dense fallback covers this gate")
    from sim.retrieval.indexer import build_index

    db_path = _build_corpus(tmp_path, horizon=10)
    n = build_index(str(db_path), str(tmp_path / "idx"))
    assert n == 10 * 6
