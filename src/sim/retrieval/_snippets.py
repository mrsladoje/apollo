"""Snippet construction shared by every retrieval backend (PLAN-B §12.2).

Token-dense, code-like format — late-interaction's strength on this kind of
input is what justifies LateOn-Code-edge over a generic dense model. The
dense fallback uses the same snippets so swapping backends does not change
the document corpus.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class HistorianSnippet:
    """A row in the retrieval corpus."""

    doc_id: str
    run_id: str
    component_id: str
    t_iso: str
    text: str


def _decode_metrics(metrics_json: str) -> str:
    """Flatten ``metrics_json`` into a token-dense ``key=value`` string."""
    try:
        d = json.loads(metrics_json) if metrics_json else {}
    except (TypeError, ValueError):
        return ""
    pieces: List[str] = []
    for k, v in sorted(d.items()):
        if isinstance(v, float):
            pieces.append(f"{k}={v:.4f}")
        else:
            pieces.append(f"{k}={v}")
    return " ".join(pieces)


def stream_snippets(historian_path: str) -> Iterable[HistorianSnippet]:
    """Yield one snippet per (run, component, t) row in the historian."""
    conn = sqlite3.connect(historian_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT run_id, component_id, t, health, status, metrics_json
           FROM component_states ORDER BY run_id, t, component_id"""
    )
    for row in rows:
        metrics_str = _decode_metrics(row["metrics_json"])
        text = (
            f"[run={row['run_id']}] [component={row['component_id']}] "
            f"[t={row['t']}] [status={row['status']}] "
            f"[health={row['health']:.2f}] {metrics_str}"
        )
        yield HistorianSnippet(
            doc_id=f"{row['run_id']}|{row['component_id']}|{row['t']}",
            run_id=row["run_id"],
            component_id=row["component_id"],
            t_iso=row["t"],
            text=text,
        )
    conn.close()


__all__ = ["HistorianSnippet", "stream_snippets"]
