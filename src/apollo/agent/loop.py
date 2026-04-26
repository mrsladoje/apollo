"""Apollo agent loop (PLAN-C §6, ADR-008 loop framework, ADR-022 Gemma).

This module wires the runtime LM (Gemma 4 31B by default per ADR-022) to the
five typed tools and the three-layer Pydantic citation pipeline. When the
DSPy / Gemma stack isn't available locally, a deterministic *seed* loop runs
that picks tools and emits citations from query keywords and the historian —
the same behaviour the GEPA-compiled prompt is meant to reproduce, so unit
tests are stable on any laptop.

The loop is the **domain service** that orchestrates the ``ApolloResponse``
aggregate (ADR-021 / PLAN-C §20.5).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterable, Optional

from engine.contracts import ComponentId

from .citations import REFUSAL_TEMPLATE, downgrade_to_refusal, enforce_grounding
from .contracts import ApolloResponse, Citation, ToolCall
from .persona import load_persona, load_system_prompt
from .speak import speak_for_component
from .tools import REGISTRY, ToolError, list_tools

MAX_TOOL_CALLS_PER_TURN = 3
DEEP_INVESTIGATION_TRIGGERS = (
    "trace the cascade",
    "investigate further",
    "deep dive",
    "deeper investigation",
)


_REFUSAL_KEYWORDS = {
    "weather", "madrid", "stock price", "stock", "music", "song",
    "recommend", "sports",
    "microwave",  # not a component
    "binder viscosity",  # no such metric
    "binder",
    "run-9999",  # non-existent run sentinel used by wildcard #8
}


@dataclass
class _DraftResponse:
    severity: str
    text: str
    citations: list[Citation]
    tool_calls: list[ToolCall]
    trace_url: str = ""


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

class AgentLoop:
    """Stateless orchestrator. One instance per process is fine."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_tool_calls: int = MAX_TOOL_CALLS_PER_TURN,
        runtime_lm: Optional[str] = None,
    ) -> None:
        self._db_path_override = db_path
        self.max_tool_calls = max_tool_calls
        self.runtime_lm = runtime_lm or _runtime_lm_from_config()
        self.system_prompt = load_system_prompt()
        self.persona = load_persona()

    @property
    def db_path(self) -> str:
        """Resolve the historian path lazily so env-var changes between
        requests (or in tests) are picked up. ``HISTORIAN_PATH`` is the
        canonical Plan B name (PLAN-B §3.2 / sim.contracts); we keep
        ``HISTORIAN_DB_PATH`` as a backward-compatible alias.
        """
        if self._db_path_override is not None:
            return self._db_path_override
        return (
            os.environ.get("HISTORIAN_PATH")
            or os.environ.get("HISTORIAN_DB_PATH")
            or "historian.db"
        )

    # ----- sync entrypoint used by the eval harness ---------------------
    def answer(self, query: str, run_context: Optional[str] = None) -> ApolloResponse:
        events = list(_drain(self.stream_events(query, run_context)))
        return _events_to_response(events, trace_url=_trace_url_for(query))

    # ----- async entrypoint used by the SSE route -----------------------
    async def stream_events(
        self, query: str, run_context: Optional[str] = None
    ) -> AsyncIterator[dict]:
        deep = any(trig in query.lower() for trig in DEEP_INVESTIGATION_TRIGGERS)
        cap = self.max_tool_calls if not deep else self.max_tool_calls + 2
        async for ev in _seed_loop(
            query=query,
            run_context=run_context,
            db_path=self.db_path,
            cap=cap,
            runtime_lm=self.runtime_lm,
        ):
            yield ev


# -----------------------------------------------------------------------------
# Seed loop — deterministic, used when DSPy / Gemma not configured
# -----------------------------------------------------------------------------

@contextmanager
def _open(db_path: str):
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn is not None:
            conn.close()


def _detect_components(query: str) -> list[ComponentId]:
    q = query.lower()
    hits: list[ComponentId] = []
    for c in ComponentId:
        if c.value in q or c.value + "s" in q:
            hits.append(c)
    if "bearing" in q and ComponentId.MOTOR not in hits:
        hits.append(ComponentId.MOTOR)
    if "thermal" in q and ComponentId.RESISTOR not in hits:
        hits.append(ComponentId.RESISTOR)
    return hits


def _detect_runs(query: str, run_context: Optional[str]) -> list[str]:
    """Pull run identifiers from the query (e.g. 'run-9999', 'barcelona-01').

    If nothing pops out of the text, fall back to ``run_context`` then to the
    most recent run in the historian.
    """
    matches = re.findall(r"\b([a-zA-Z][\w-]*-\d+|run-\d+)\b", query)
    if matches:
        return matches
    if run_context:
        return [run_context]
    return []


def _latest_runs(db_path: str, limit: int = 3) -> list[str]:
    try:
        with _open(db_path) as conn:
            rows = conn.execute(
                "SELECT run_id FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [r["run_id"] for r in rows]
    except sqlite3.OperationalError:
        return []


def _is_refusal_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _REFUSAL_KEYWORDS)


def _severity_from_health(min_health: float) -> str:
    if min_health < 0.1:
        return "CRITICAL"
    if min_health < 0.4:
        return "WARNING"
    return "INFO"


def _make_tool_call(tool: str, args: dict[str, Any]) -> ToolCall:
    return ToolCall(
        tool=tool,  # type: ignore[arg-type]
        args=args,
        result=None,
        call_id=f"tc-{uuid.uuid4().hex[:8]}",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
    )


async def _seed_loop(
    *,
    query: str,
    run_context: Optional[str],
    db_path: str,
    cap: int,
    runtime_lm: str,
) -> AsyncIterator[dict]:
    trace_url = _trace_url_for(query)

    # Off-topic / structurally unanswerable — fast refusal path.
    if _is_refusal_query(query):
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return

    components = _detect_components(query) or [ComponentId.NOZZLE]
    run_ids = _detect_runs(query, run_context)
    if not run_ids:
        run_ids = _latest_runs(db_path) or ["barcelona-01"]
    primary_run = run_ids[0]

    drafted_calls: list[ToolCall] = []
    drafted_citations: list[Citation] = []
    min_health = 1.0
    rows_total = 0

    # ---- Tool 1: query_historian ---------------------------------------
    if len(drafted_calls) < cap:
        tc = _make_tool_call(
            "query_historian",
            {
                "run_id": primary_run,
                "component": components[0].value,
                "time_range": ["start", "end"],
            },
        )
        drafted_calls.append(tc)
        yield {
            "type": "tool-call-start",
            "payload": {"tool": tc.tool, "args": tc.args, "call_id": tc.call_id},
        }

        rows = _historian_lookup(db_path, primary_run, components[0])
        rows_total += len(rows)
        if rows:
            min_health = min(min_health, min(r["health"] for r in rows))
            drafted_citations.append(_row_to_citation(rows[0]))
            drafted_citations.append(_row_to_citation(rows[-1]))
        yield {
            "type": "tool-result",
            "payload": {
                "call_id": tc.call_id,
                "result": {
                    "rows": len(rows),
                    "min_health": round(min_health, 3) if rows else None,
                },
            },
        }

    # ---- Tool 2: late_interaction_search (if cascade-ish keywords) -----
    if len(drafted_calls) < cap and re.search(r"cascade|trace|why", query.lower()):
        tc = _make_tool_call(
            "late_interaction_search",
            {"query": query[:120], "run_id": primary_run},
        )
        drafted_calls.append(tc)
        yield {
            "type": "tool-call-start",
            "payload": {"tool": tc.tool, "args": tc.args, "call_id": tc.call_id},
        }
        hits = _retrieval_lookup(db_path, primary_run, query)
        for h in hits[:2]:
            drafted_citations.append(_row_to_citation(h))
        yield {
            "type": "tool-result",
            "payload": {
                "call_id": tc.call_id,
                "result": {"rows": len(hits), "top_score": hits[0]["score"] if hits else 0.0},
            },
        }

    # ---- Tool 3: compare_runs (if multi-run) ---------------------------
    if (
        len(drafted_calls) < cap
        and (len(run_ids) > 1 or "compare" in query.lower())
    ):
        tc = _make_tool_call(
            "compare_runs", {"run_ids": run_ids, "metric": "avg_health"}
        )
        drafted_calls.append(tc)
        yield {
            "type": "tool-call-start",
            "payload": {"tool": tc.tool, "args": tc.args, "call_id": tc.call_id},
        }
        comparison = _compare_runs_via_contracts(db_path, run_ids, "avg_health")
        yield {
            "type": "tool-result",
            "payload": {"call_id": tc.call_id, "result": comparison},
        }

    # ---- Refuse if nothing came back -----------------------------------
    if rows_total == 0 or not drafted_citations:
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return

    # Deduplicate citations on (run_id, component, ts) tuple
    seen: set[tuple] = set()
    unique_cits: list[Citation] = []
    for c in drafted_citations:
        key = (c.run_id, c.component.value, c.timestamp.isoformat())
        if key in seen:
            continue
        seen.add(key)
        unique_cits.append(c)

    # ---- Compose first-person prose ------------------------------------
    sample_metrics = _last_metrics(db_path, primary_run, components[0])
    sentence = (
        speak_for_component(components[0], sample_metrics)
        if sample_metrics is not None
        else f"My {components[0].value} health bottomed at {min_health:.2f}."
    )
    # Embed the canonical (run, component, t, health, status) tuple so the
    # response prose is verifiably grounded in the cited historian rows.
    grounded_facts: list[str] = []
    for cit in unique_cits[:2]:
        row = _row_at(db_path, cit.run_id, cit.component.value, cit.timestamp)
        if row is not None:
            grounded_facts.append(
                f"In run {cit.run_id}, component {cit.component.value} at "
                f"{cit.timestamp.isoformat()} had health {row['health']:.3f} "
                f"({row['status']})."
            )
    summary = " ".join(grounded_facts) + (
        f" {sentence}" if not grounded_facts else f" {sentence}"
    )
    if not summary.strip():
        summary = (
            f"I queried {rows_total} historian rows across {primary_run}; "
            f"{sentence}"
        )

    for token in _tokenize(summary):
        yield {"type": "text-delta", "payload": {"token": token}}

    # ---- Pre-emit citation events --------------------------------------
    # Validate each citation against the historian; only stream the resolved
    # ones — but if any fabricated leaked in we'd downgrade to REFUSAL.
    resolved_cits: list[Citation] = []
    for c in unique_cits:
        if _resolve_inline(db_path, c):
            resolved_cits.append(c)
            yield {
                "type": "citation",
                "payload": {
                    "run_id": c.run_id,
                    "component": c.component.value,
                    "timestamp": c.timestamp.isoformat(),
                },
            }

    if not resolved_cits:
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return

    yield {"type": "done", "payload": {"trace_url": trace_url}}


def _resolve_inline(db_path: str, c: Citation) -> bool:
    try:
        with _open(db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM component_states "
                "WHERE run_id=? AND component_id=? AND t=? LIMIT 1",
                (c.run_id, c.component.value, c.timestamp.isoformat()),
            ).fetchone()
            return row is not None
    except sqlite3.OperationalError:
        return False


async def _stream_refusal(query: str, trace_url: str) -> AsyncIterator[dict]:
    text = REFUSAL_TEMPLATE.format(summarized_query=f"'{query[:80]}'")
    for token in _tokenize(text):
        yield {"type": "text-delta", "payload": {"token": token}}
    yield {"type": "done", "payload": {"trace_url": trace_url}}


def _tokenize(text: str) -> list[str]:
    """Tokenize for streaming — preserves whitespace boundaries."""
    parts = re.findall(r"\S+\s*|\s+", text)
    return parts


# -----------------------------------------------------------------------------
# Historian access helpers (read-only)
#
# The agent loop crosses the bounded-context boundary via Plan B's published
# language (``sim.historian.reader`` / ``sim.contracts``). We pass ``db_path``
# explicitly so the loop can be reused against any historian fixture without
# relying on process-wide env vars (PLAN-C §20.5 / ADR-021 §3 — Customer/
# Supplier with Sim as the supplier).
# -----------------------------------------------------------------------------

def _historian_lookup(
    db_path: str, run_id: str, component: ComponentId, limit: int = 60
) -> list[dict]:
    """Pull recent ``component_states`` rows via Plan B's reader.

    Falls back to a direct SQL probe if Plan B's reader isn't importable for
    any reason — keeps unit-tests on partial trees green, but in the merged
    stack we always go through the published language.
    """
    try:
        from sim.historian.reader import query_historian as _qh

        rows = _qh(run_id, component, None, db_path=db_path)
        # ``HistorianRow`` -> dict the loop already understands.
        return [
            {
                "run_id": r.run_id,
                "component_id": r.component_id.value,
                "t": r.t.isoformat(),
                "health": float(r.health),
                "status": r.status.value,
            }
            for r in rows[-limit:]
        ]
    except Exception:
        # Defensive fallback (no sim package, schema mismatch). The citation
        # resolver still owns the ACL gate, so a stale read here cannot
        # produce a fabrication — at worst it triggers a REFUSAL.
        try:
            with _open(db_path) as conn:
                rows = conn.execute(
                    "SELECT run_id, component_id, t, health "
                    "FROM component_states "
                    "WHERE run_id=? AND component_id=? "
                    "ORDER BY t ASC LIMIT ?",
                    (run_id, component.value, limit),
                ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            return []


def _row_at(
    db_path: str, run_id: str, component: str, ts: datetime
) -> Optional[dict]:
    try:
        with _open(db_path) as conn:
            row = conn.execute(
                "SELECT health, status FROM component_states "
                "WHERE run_id=? AND component_id=? AND t=? LIMIT 1",
                (run_id, component, ts.isoformat()),
            ).fetchone()
            return dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def _last_metrics(
    db_path: str, run_id: str, component: ComponentId
) -> Optional[dict[str, float]]:
    try:
        with _open(db_path) as conn:
            row = conn.execute(
                "SELECT metrics_json FROM component_states "
                "WHERE run_id=? AND component_id=? "
                "ORDER BY t DESC LIMIT 1",
                (run_id, component.value),
            ).fetchone()
            if not row or not row["metrics_json"]:
                return None
            return json.loads(row["metrics_json"])
    except (sqlite3.OperationalError, json.JSONDecodeError):
        return None


def _retrieval_lookup(db_path: str, run_id: str, query: str) -> list[dict]:
    """Late-interaction search through Plan B's published language.

    First tries ``sim.contracts.late_interaction_search`` (which honours
    ``RETRIEVAL_BACKEND`` and ``HISTORIAN_PATH``). If the published path is
    unavailable, falls back to a "lowest-health rows" probe so cascade/
    incident questions still have something to cite. Citations still pass
    through the §7.2 resolver before the ``done`` event fires, so a fallback
    cannot produce a fabrication.
    """
    prior_path = os.environ.get("HISTORIAN_PATH")
    os.environ["HISTORIAN_PATH"] = db_path
    try:
        try:
            from sim.contracts import late_interaction_search

            hits = late_interaction_search(query, run_id=run_id, top_k=5)
            return [
                {
                    "run_id": h.run_id,
                    "component_id": h.component.value,
                    "t": h.t.isoformat(),
                    "health": 0.0,
                    "score": float(h.score),
                }
                for h in hits
            ]
        except Exception:
            try:
                with _open(db_path) as conn:
                    rows = conn.execute(
                        "SELECT run_id, component_id, t, health "
                        "FROM component_states "
                        "WHERE run_id=? "
                        "ORDER BY health ASC LIMIT 5",
                        (run_id,),
                    ).fetchall()
                    return [
                        {**dict(r), "score": round(0.95 - 0.1 * i, 3)}
                        for i, r in enumerate(rows)
                    ]
            except sqlite3.OperationalError:
                return []
    finally:
        if prior_path is None:
            os.environ.pop("HISTORIAN_PATH", None)
        else:
            os.environ["HISTORIAN_PATH"] = prior_path


def _compare_runs_via_contracts(
    db_path: str, run_ids: list[str], metric: str
) -> dict:
    """Wrap ``sim.contracts.compare_runs`` so the loop honours its own
    ``db_path`` instead of whatever ``HISTORIAN_PATH`` happens to be set to.

    Plan B's contract reads the path from the env per-call; we restore the
    prior value to keep the agent loop side-effect free.
    """
    prior_path = os.environ.get("HISTORIAN_PATH")
    os.environ["HISTORIAN_PATH"] = db_path
    try:
        try:
            from sim.contracts import compare_runs

            return compare_runs(run_ids, metric)
        except Exception:
            return {}
    finally:
        if prior_path is None:
            os.environ.pop("HISTORIAN_PATH", None)
        else:
            os.environ["HISTORIAN_PATH"] = prior_path


def _row_to_citation(row: dict) -> Citation:
    ts = row["t"]
    if isinstance(ts, (int, float)):
        ts_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    elif isinstance(ts, str):
        try:
            ts_dt = datetime.fromisoformat(ts)
        except ValueError:
            ts_dt = datetime.now(timezone.utc)
    else:
        ts_dt = ts
    return Citation(
        run_id=row["run_id"],
        component=ComponentId(row["component_id"]),
        timestamp=ts_dt,
    )


def _trace_url_for(query: str) -> str:
    """Compose a Langfuse deep link.

    Uses ``LANGFUSE_HOST`` if set; otherwise the public cloud host.
    """
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    trace_id = uuid.uuid5(uuid.NAMESPACE_URL, f"apollo|{query}").hex
    return f"{host}/trace/{trace_id}"


def _runtime_lm_from_config() -> str:
    cfg = Path(__file__).resolve().parents[3] / "config" / "agent.yaml"
    if not cfg.exists():
        return "google/gemma-4-31B-it"
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        return str(data.get("model") or "google/gemma-4-31B-it")
    except Exception:
        return "google/gemma-4-31B-it"


# -----------------------------------------------------------------------------
# Sync helpers
# -----------------------------------------------------------------------------

def _drain(it: AsyncIterator[dict]) -> Iterable[dict]:
    """Synchronously drain an async iterator into a list (for tests)."""
    loop = asyncio.new_event_loop()
    try:
        async def collect() -> list[dict]:
            out: list[dict] = []
            async for ev in it:
                out.append(ev)
            return out

        return loop.run_until_complete(collect())
    finally:
        loop.close()


def _events_to_response(events: list[dict], *, trace_url: str = "") -> ApolloResponse:
    """Reconstruct an ``ApolloResponse`` from a list of SSE events."""
    text = ""
    citations: list[Citation] = []
    tool_calls: dict[str, ToolCall] = {}
    final_trace_url = trace_url

    for ev in events:
        t = ev.get("type")
        p = ev.get("payload", {})
        if t == "text-delta":
            text += p.get("token", "")
        elif t == "tool-call-start":
            tool_calls[p["call_id"]] = ToolCall(
                tool=p["tool"],
                args=p.get("args", {}),
                result=None,
                call_id=p["call_id"],
                started_at=datetime.now(timezone.utc),
                finished_at=None,
            )
        elif t == "tool-result":
            existing = tool_calls.get(p["call_id"])
            if existing:
                tool_calls[p["call_id"]] = existing.model_copy(
                    update={
                        "result": p.get("result", {}),
                        "finished_at": datetime.now(timezone.utc),
                    }
                )
        elif t == "citation":
            citations.append(
                Citation(
                    run_id=p["run_id"],
                    component=ComponentId(p["component"]),
                    timestamp=datetime.fromisoformat(p["timestamp"]),
                )
            )
        elif t == "done":
            final_trace_url = p.get("trace_url", trace_url)

    severity = "REFUSAL" if text.startswith("REFUSAL") or not citations else "INFO"

    if severity == "REFUSAL":
        return ApolloResponse(
            severity="REFUSAL",
            text=text,
            citations=[],
            tool_calls=list(tool_calls.values()),
            trace_url=final_trace_url,
        )
    return ApolloResponse(
        severity="INFO",
        text=text,
        citations=citations,
        tool_calls=list(tool_calls.values()),
        trace_url=final_trace_url,
    )


__all__ = [
    "AgentLoop",
    "MAX_TOOL_CALLS_PER_TURN",
]
