"""Dense retrieval fallback — PLAN-B §12.5 / ADR-010 R-3.

The plan calls for Voyage-3 or OpenAI text-embedding-3-large here, both of
which require network credentials. To stay in spec for the offline demo
(R-7), this fallback uses a hash-trick TF-IDF embedding — same query/return
shape as the real dense path, no external services. ``RETRIEVAL_BACKEND=dense``
flips to this in one env var (§12.5: "5-second config flip").

Determinism: a single in-memory index is built lazily on first query from
``HISTORIAN_PATH`` (default ``historian.db``). Two queries against the same
corpus return identical scores.
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from engine.contracts import ComponentId
from sim.contracts import RetrievedRow

from ._snippets import HistorianSnippet, stream_snippets

# Hash-trick dimension. 1024 keeps the math fast (NFR-4) and recall sane
# enough on the kind of token-dense snippets the indexer emits.
_DIM = 1024
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

_index_state: Optional[Dict] = None


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _embed(tokens: List[str], idf: Dict[int, float]) -> List[float]:
    vec = [0.0] * _DIM
    if not tokens:
        return vec
    counts: Dict[int, int] = {}
    for tok in tokens:
        h = hash(tok) % _DIM
        counts[h] = counts.get(h, 0) + 1
    inv_len = 1.0 / len(tokens)
    for h, c in counts.items():
        tf = c * inv_len
        vec[h] = tf * idf.get(h, 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _build_index(historian_path: str) -> Dict:
    """Materialize a hash-trick TF-IDF index over every historian row."""
    snippets: List[HistorianSnippet] = list(stream_snippets(historian_path))
    n_docs = max(1, len(snippets))

    # Document-frequency over hashed buckets.
    df: Dict[int, int] = {}
    tokenized: List[List[str]] = []
    for snip in snippets:
        toks = _tokenize(snip.text)
        tokenized.append(toks)
        seen: set = set()
        for tok in toks:
            h = hash(tok) % _DIM
            if h in seen:
                continue
            seen.add(h)
            df[h] = df.get(h, 0) + 1
    idf = {h: math.log((n_docs + 1) / (c + 1)) + 1.0 for h, c in df.items()}

    embeddings: List[List[float]] = [_embed(toks, idf) for toks in tokenized]
    return {
        "snippets": snippets,
        "embeddings": embeddings,
        "idf": idf,
        "historian_path": historian_path,
    }


def _ensure_index(historian_path: str) -> Dict:
    global _index_state
    if _index_state is None or _index_state["historian_path"] != historian_path:
        _index_state = _build_index(historian_path)
    return _index_state


def reset_index() -> None:
    """Test hook — clears the in-memory cache so the next query rebuilds."""
    global _index_state
    _index_state = None


def late_interaction_search(
    query: str,
    run_id: Optional[str] = None,
    top_k: int = 10,
) -> List[RetrievedRow]:
    """Dense-fallback search. Same signature as ``§3.2``; same return type."""
    historian_path = os.environ.get("HISTORIAN_PATH", "historian.db")
    state = _ensure_index(historian_path)

    if not state["snippets"]:
        return []

    q_emb = _embed(_tokenize(query), state["idf"])

    scored: List[Tuple[float, int]] = []
    for i, doc_emb in enumerate(state["embeddings"]):
        score = 0.0
        for a, b in zip(q_emb, doc_emb):
            score += a * b
        scored.append((score, i))

    scored.sort(key=lambda p: p[0], reverse=True)

    out: List[RetrievedRow] = []
    for score, i in scored:
        snip = state["snippets"][i]
        if run_id and snip.run_id != run_id:
            continue
        out.append(
            RetrievedRow(
                run_id=snip.run_id,
                component=ComponentId(snip.component_id),
                t=datetime.fromisoformat(snip.t_iso),
                score=float(score),
                snippet=snip.text,
            )
        )
        if len(out) >= top_k:
            break
    return out


__all__ = ["late_interaction_search", "reset_index"]
