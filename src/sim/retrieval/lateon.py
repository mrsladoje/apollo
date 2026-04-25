"""Real LateOn-Code-edge search — PLAN-B §12.3.

Reads the index built by ``sim.retrieval.indexer``. Lazy-imports ``pylate``
so callers without the dep can keep importing ``sim.retrieval`` for the
mock/dense paths.

``RETRIEVAL_BACKEND=lateon`` switches ``sim.api.late_interaction_search`` to
this module. The over-fetch + filter pattern (``top_k * 3``) ensures the
``run_id`` filter still returns ``top_k`` rows when filtering excludes hits.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

from engine.contracts import ComponentId
from sim.contracts import RetrievedRow
from sim.retrieval._snippets import stream_snippets

DEFAULT_INDEX_PATH = "data/lateon.index"
DEFAULT_MODEL = "lightonai/lateon-code-edge"

_model = None
_index = None
_retriever = None
_snippet_lookup: Dict[str, str] = {}
_loaded_index_path: Optional[str] = None


class LateOnUnavailable(RuntimeError):
    """Raised when ``pylate`` or the index folder is missing."""


def _ensure_loaded(index_path: str, model_name: str) -> None:
    global _model, _index, _retriever, _snippet_lookup, _loaded_index_path
    if _model is not None and _loaded_index_path == index_path:
        return
    try:
        from pylate import indexes, models, retrieve  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised on offline CI
        raise LateOnUnavailable(
            "pylate is not installed; install PLAN-B requirements before retrieval"
        ) from exc
    if not os.path.isdir(index_path):
        raise LateOnUnavailable(
            f"LateOn index not found at {index_path!r}; "
            "run `python -m sim.retrieval.indexer --out " + index_path + "` first"
        )
    _model = models.ColBERT(model_name)
    _index = indexes.PLAID(index_folder=index_path, override=False)
    _retriever = retrieve.ColBERT(index=_index)
    historian_path = os.environ.get("HISTORIAN_PATH", "historian.db")
    _snippet_lookup = {s.doc_id: s.text for s in stream_snippets(historian_path)}
    _loaded_index_path = index_path


def late_interaction_search(
    query: str,
    run_id: Optional[str] = None,
    top_k: int = 10,
) -> List[RetrievedRow]:
    index_path = os.environ.get("LATEON_INDEX_PATH", DEFAULT_INDEX_PATH)
    model_name = os.environ.get("LATEON_MODEL", DEFAULT_MODEL)
    _ensure_loaded(index_path, model_name)

    q_emb = _model.encode([query], is_query=True)
    hits = _retriever.retrieve(queries_embeddings=q_emb, k=top_k * 3)

    out: List[RetrievedRow] = []
    for hit in hits[0]:
        doc_id = hit["id"]
        score = float(hit["score"])
        snippet = _snippet_lookup.get(doc_id, "")
        run, comp, t_iso = doc_id.split("|", 2)
        if run_id and run != run_id:
            continue
        out.append(
            RetrievedRow(
                run_id=run,
                component=ComponentId(comp),
                t=datetime.fromisoformat(t_iso),
                score=score,
                snippet=snippet,
            )
        )
        if len(out) >= top_k:
            break
    return out


__all__ = ["late_interaction_search", "LateOnUnavailable"]
