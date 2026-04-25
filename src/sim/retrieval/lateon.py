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
from typing import List, Optional

from engine.contracts import ComponentId
from sim.contracts import RetrievedRow

DEFAULT_INDEX_PATH = "data/lateon.index"
DEFAULT_MODEL = "lightonai/lateon-code-edge"

_model = None
_index = None
_loaded_index_path: Optional[str] = None


class LateOnUnavailable(RuntimeError):
    """Raised when ``pylate`` or the index folder is missing."""


def _ensure_loaded(index_path: str, model_name: str) -> None:
    global _model, _index, _loaded_index_path
    if _model is not None and _loaded_index_path == index_path:
        return
    try:
        from pylate import indexes, models  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised on offline CI
        raise LateOnUnavailable(
            "pylate is not installed; install it or set RETRIEVAL_BACKEND=mock|dense"
        ) from exc
    if not os.path.isdir(index_path):
        raise LateOnUnavailable(
            f"LateOn index not found at {index_path!r}; "
            "run `python -m sim.retrieval.indexer --out " + index_path + "` first"
        )
    _model = models.ColBERT(model_name)
    _index = indexes.PLAID(index_folder=index_path, override=False)
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
    hits = _index.search(queries_embeddings=q_emb, k=top_k * 3)

    out: List[RetrievedRow] = []
    for hit in hits[0]:
        # PyLate hit objects expose ``id``, ``score``, and ``document``.
        doc_id = getattr(hit, "id", None) or hit["id"]
        score = float(getattr(hit, "score", None) or hit["score"])
        snippet = getattr(hit, "document", None) or hit.get("document", "")
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
