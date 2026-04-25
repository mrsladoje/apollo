"""PyLate / PLAID index builder — PLAN-B §12.1.

Lazy-imports ``pylate`` so machines without the heavy dep can still load
the rest of the package (R-7 / offline CI). Snippet construction is shared
with the dense fallback via ``_snippets.stream_snippets`` so the corpus
matches across backends.

Run as a script:

    python -m sim.retrieval.indexer --historian historian.db --out data/lateon.index
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable, List

from ._snippets import HistorianSnippet, stream_snippets

DEFAULT_INDEX_PATH = "data/lateon.index"
DEFAULT_MODEL = "lightonai/lateon-code-edge"


def build_index(
    historian_path: str = "historian.db",
    index_path: str = DEFAULT_INDEX_PATH,
    model_name: str = DEFAULT_MODEL,
) -> int:
    """Build the late-interaction index. Returns the number of indexed docs.

    Per ADR-010 the corpus stays small (<= 12k rows for the demo) so a single
    encode+add pass is cheap. Re-running with ``override=True`` rewrites the
    folder so this is the canonical "rebuild the demo index" entry point.
    """
    from pylate import indexes, models  # type: ignore  # heavy, lazy

    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)

    model = models.ColBERT(model_name)
    index = indexes.PLAID(index_folder=index_path, override=True)

    snippets: List[HistorianSnippet] = list(stream_snippets(historian_path))
    if not snippets:
        return 0

    docs = [s.text for s in snippets]
    doc_ids = [s.doc_id for s in snippets]

    embeddings = model.encode(docs, is_query=False)
    index.add_documents(documents_ids=doc_ids, documents_embeddings=embeddings)
    return len(snippets)


def _cli() -> None:  # pragma: no cover
    p = argparse.ArgumentParser(description="Build the LateOn-Code-edge index.")
    p.add_argument("--historian", default="historian.db")
    p.add_argument("--out", default=DEFAULT_INDEX_PATH)
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args()
    n = build_index(args.historian, args.out, args.model)
    print(f"Indexed {n} documents into {args.out}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
