"""§12.7 — real PyLate / LateOn index build and search acceptance."""

from __future__ import annotations

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


def test_pylate_indexer_writes_real_plaid_artifact(tmp_path, monkeypatch):
    from sim.retrieval.indexer import build_index

    db_path = _build_corpus(tmp_path, horizon=10)
    index_path = tmp_path / "idx"
    n = build_index(str(db_path), str(index_path))
    n_again = build_index(str(db_path), str(index_path))
    assert n == 10 * 6
    assert n_again == n
    assert index_path.exists()
    assert not (tmp_path / "idx.tmp").exists()
    assert not (index_path / "manifest.json").exists()


def test_lateon_search_returns_typed_rows(tmp_path, monkeypatch):
    from sim.retrieval import lateon
    from sim.retrieval.indexer import build_index

    db_path = _build_corpus(tmp_path, horizon=10)
    index_path = tmp_path / "idx"
    build_index(str(db_path), str(index_path))
    monkeypatch.setenv("LATEON_INDEX_PATH", str(index_path))
    monkeypatch.setenv("HISTORIAN_PATH", str(db_path))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    lateon._model = None
    lateon._index = None
    lateon._retriever = None

    rows = lateon.late_interaction_search("heater thermal cascade", top_k=3)

    assert rows
    assert all(r.snippet.startswith("[run=") for r in rows)
