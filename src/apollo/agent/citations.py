"""Citation resolution + refusal pipeline (PLAN-C §7, ADR-014).

This module is the **Anti-Corruption Layer** between the Agent context and the
Historian (Plan B). See ADR-021 §3 and PLAN-C §20.8.

Three enforcement layers (PLAN-C §7.1):
  1. Pydantic schema validation (in ``contracts.py``)
  2. Citation resolution against historian PK (here)
  3. Refusal-template emission (here)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Iterable

from .contracts import ApolloResponse, Citation


REFUSAL_TEMPLATE = (
    "REFUSAL — I cannot answer that from the data I have. The historian "
    "returned no rows matching {summarized_query}. I will not guess. Try a "
    "different run, component, or time window."
)


def _db_path() -> str:
    return os.environ.get("HISTORIAN_DB_PATH", "historian.db")


def _open_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_ts(ts: datetime) -> str:
    """Historian rows store ISO timestamps; align timezone handling.

    The historian writer (Plan B) persists ``datetime.isoformat()`` strings.
    We accept aware/naive datetimes and emit a matching ISO string.
    """
    return ts.isoformat()


def resolve_citation(c: Citation, db: sqlite3.Connection | None = None) -> bool:
    """Return True iff ``(run_id, component, t)`` hits a real row in
    ``component_states`` OR a row in ``drivers`` (the two tables citations may
    point at). PLAN-C §7.2.

    Falls back to ``True`` only when the database is missing — in that case the
    Pydantic layer is the only line of defence and tests must mock this hook.
    """
    own = db is None
    conn: sqlite3.Connection | None = None
    try:
        if own:
            try:
                conn = _open_db()
            except sqlite3.Error:
                return False
        else:
            conn = db
        ts = _normalize_ts(c.timestamp)
        sql = (
            "SELECT 1 FROM component_states "
            " WHERE run_id = ? AND component_id = ? AND t = ? "
            "UNION "
            "SELECT 1 FROM drivers "
            " WHERE run_id = ? AND t = ? "
            "LIMIT 1"
        )
        try:
            row = conn.execute(
                sql, (c.run_id, c.component.value, ts, c.run_id, ts)
            ).fetchone()
        except sqlite3.OperationalError:
            # Schema not present — historian unavailable. Treat as unresolved
            # so callers downgrade to REFUSAL rather than ship a fabrication.
            return False
        return row is not None
    finally:
        if own and conn is not None:
            conn.close()


def downgrade_to_refusal(
    response: ApolloResponse,
    summarized_query: str = "the cited rows",
) -> ApolloResponse:
    """Return a REFUSAL aggregate that drops all citations.

    Reuses the original ``tool_calls`` / ``trace_url`` so the audit trail
    survives — the user still sees what we tried.
    """
    return ApolloResponse(
        severity="REFUSAL",
        text=REFUSAL_TEMPLATE.format(summarized_query=summarized_query),
        citations=[],
        tool_calls=response.tool_calls,
        trace_url=response.trace_url,
    )


def enforce_grounding(
    response: ApolloResponse,
    db: sqlite3.Connection | None = None,
    summarized_query: str = "the cited rows",
) -> ApolloResponse:
    """Layer-2 + Layer-3 enforcement.

    If any citation fails to resolve, downgrade the entire aggregate to
    REFUSAL with empty citations (PLAN-C §7.1 — no partial credit).
    """
    if response.severity == "REFUSAL":
        return response  # already refusing — leave alone

    if not response.citations:
        # Pydantic should have caught this, but belt-and-braces:
        return downgrade_to_refusal(response, summarized_query)

    own = db is None
    conn: sqlite3.Connection | None = None
    try:
        if own:
            try:
                conn = _open_db()
            except sqlite3.Error:
                conn = None
        else:
            conn = db

        # If we couldn't open the historian we have to refuse — better safe
        # than fabricated.
        if conn is None:
            return downgrade_to_refusal(response, summarized_query)

        for c in response.citations:
            if not resolve_citation(c, conn):
                return downgrade_to_refusal(response, summarized_query)
        return response
    finally:
        if own and conn is not None:
            conn.close()


def all_citations_resolve(
    citations: Iterable[Citation],
    db: sqlite3.Connection | None = None,
) -> bool:
    return all(resolve_citation(c, db) for c in citations)


__all__ = [
    "REFUSAL_TEMPLATE",
    "all_citations_resolve",
    "downgrade_to_refusal",
    "enforce_grounding",
    "resolve_citation",
]
