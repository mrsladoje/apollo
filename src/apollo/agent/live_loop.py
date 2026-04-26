"""Live Gemma-backed Apollo runtime loop.

This is the ADR-022 runtime path: Gemma chooses a typed tool, Apollo executes
the tool through the registry, then Gemma writes a grounded final answer from
the tool result. The deterministic seed loop remains available for tests and
offline demos, but the app should use this module by default.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from engine.contracts import ComponentId, ROW_ORDER

from .citations import REFUSAL_TEMPLATE
from .contracts import Citation
from .tools import ToolError, invoke

_APOLLO_RUN = "barcelona-humid-ai-seed0042"
_FIXED_RUN = "barcelona-humid-fixed-seed0042"
_DARK_TWIN_RUN = "barcelona-humid-none-seed0042"
_KNOWN_RUNS = (
    _APOLLO_RUN,
    _FIXED_RUN,
    "barcelona-humid-none-seed0042",
    "phoenix-dry-ai-seed0042",
    "phoenix-dry-fixed-seed0042",
    "phoenix-dry-none-seed0042",
    "stressed-ai-seed0042",
    "stressed-fixed-seed0042",
    "stressed-none-seed0042",
)


async def stream_live_events(
    *,
    query: str,
    run_context: str | None,
    db_path: str,
    cap: int,
    system_prompt: str,
    runtime_lm: str,
) -> AsyncIterator[dict]:
    """Stream one live Gemma turn as Apollo SSE events."""
    trace_url = _trace_url_for(query)
    if not os.environ.get("GEMMA_API_KEY"):
        async for ev in _stream_refusal(
            "Gemma runtime is not configured: GEMMA_API_KEY is missing.",
            trace_url,
        ):
            yield ev
        return

    if _wants_all_component_history(query):
        async for ev in _stream_all_component_plots(query, db_path, trace_url, system_prompt, runtime_lm):
            yield ev
        return

    if _wants_run_comparison(query, run_context):
        args = {
            "run_ids": _infer_compare_run_ids(query, run_context),
            "metric": _infer_compare_metric(query),
        }
        async for ev in _execute_and_answer(
            query=query,
            db_path=db_path,
            trace_url=trace_url,
            system_prompt=system_prompt,
            runtime_lm=runtime_lm,
            tool="compare_runs",
            args=args,
        ):
            yield ev
        return

    try:
        selection = _select_tool(query, run_context, system_prompt, runtime_lm)
    except Exception as exc:  # noqa: BLE001
        async for ev in _stream_refusal(f"Gemma router failed: {exc}", trace_url):
            yield ev
        return

    tool = str(selection.get("tool", "")).strip()
    if tool == "REFUSAL":
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return

    if _wants_all_component_history(query) and tool in {"plot_component_history", "query_historian"}:
        async for ev in _stream_all_component_plots(query, db_path, trace_url, system_prompt, runtime_lm):
            yield ev
        return

    args = _normalize_args(tool, selection.get("args") or {}, query, run_context)
    async for ev in _execute_and_answer(
        query=query,
        db_path=db_path,
        trace_url=trace_url,
        system_prompt=system_prompt,
        runtime_lm=runtime_lm,
        tool=tool,
        args=args,
    ):
        yield ev


def _select_tool(
    query: str,
    run_context: str | None,
    system_prompt: str,
    runtime_lm: str,
) -> dict[str, Any]:
    prompt = (
        _tool_router_prompt(run_context)
        + "\nQuestion: "
        + query
        + "\nJSON:"
    )
    return _json_from_text(_complete(system_prompt, prompt, runtime_lm, max_tokens=500))


async def _stream_all_component_plots(
    query: str,
    db_path: str,
    trace_url: str,
    system_prompt: str,
    runtime_lm: str,
) -> AsyncIterator[dict]:
    run_id = _infer_run_id(query, None) or _DARK_TWIN_RUN
    tool_results: list[dict[str, Any]] = []
    citations: list[Citation] = []
    for component in ROW_ORDER:
        args = {"run_id": run_id, "component": component.value}
        call_id = f"tc-{uuid.uuid4().hex[:8]}"
        yield {"type": "tool-call-start", "payload": {"tool": "plot_component_history", "args": args, "call_id": call_id}}
        try:
            with _historian_env(db_path):
                result = invoke("plot_component_history", args)
        except ToolError as exc:
            yield {"type": "tool-result", "payload": {"call_id": call_id, "result": {"error": str(exc)}}}
            continue
        yield {"type": "tool-result", "payload": {"call_id": call_id, "result": result}}
        tool_results.append({"component": component.value, "result": result})
        citations.extend(_citations_for_component(db_path, run_id, component))

    if not tool_results:
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return

    fallback = (
        f"I plotted all six dark-twin component histories for {run_id}: "
        + ", ".join(c.value for c in ROW_ORDER)
        + "."
    )
    text = _answer_from_result(
        query=query,
        system_prompt=system_prompt,
        runtime_lm=runtime_lm,
        tool="plot_component_history",
        args={"run_id": run_id, "components": [c.value for c in ROW_ORDER]},
        result={"charts": tool_results},
        fallback=fallback,
    )
    if not all(component.value in text.lower() for component in ROW_ORDER):
        text = fallback
    for token in _tokenize(text):
        yield {"type": "text-delta", "payload": {"token": token}}
    for citation in _dedupe_citations(citations):
        yield {"type": "citation", "payload": _citation_payload(citation)}
    yield {"type": "done", "payload": {"trace_url": trace_url}}


async def _execute_and_answer(
    *,
    query: str,
    db_path: str,
    trace_url: str,
    system_prompt: str,
    runtime_lm: str,
    tool: str,
    args: dict[str, Any],
    fallback: str | None = None,
) -> AsyncIterator[dict]:
    call_id = f"tc-{uuid.uuid4().hex[:8]}"
    yield {"type": "tool-call-start", "payload": {"tool": tool, "args": args, "call_id": call_id}}
    try:
        with _historian_env(db_path):
            result = invoke(tool, args)
    except ToolError as exc:
        yield {"type": "tool-result", "payload": {"call_id": call_id, "result": {"error": str(exc)}}}
        async for ev in _stream_refusal(f"tool {tool} with args {args}", trace_url):
            yield ev
        return

    yield {"type": "tool-result", "payload": {"call_id": call_id, "result": result}}
    citations = _citations_from_tool_result(tool, args, result, db_path)
    if fallback is None and tool == "compare_runs":
        fallback = _compare_runs_fallback(query, args, result)
    text = _answer_from_result(query, system_prompt, runtime_lm, tool, args, result, fallback=fallback)
    for token in _tokenize(text):
        yield {"type": "text-delta", "payload": {"token": token}}
    for citation in _dedupe_citations(citations):
        yield {"type": "citation", "payload": _citation_payload(citation)}
    if not citations and tool in {"query_historian", "late_interaction_search"}:
        async for ev in _stream_refusal(query, trace_url):
            yield ev
        return
    yield {"type": "done", "payload": {"trace_url": trace_url}}


def _answer_from_result(
    query: str,
    system_prompt: str,
    runtime_lm: str,
    tool: str,
    args: dict[str, Any],
    result: Any,
    fallback: str | None = None,
) -> str:
    prompt = f"""\
Question: {query}
Tool used: {tool}
Tool args: {json.dumps(args, default=str)}
Tool result/context:
{json.dumps(result, default=str, ensure_ascii=False)[:12000]}

Return only JSON with keys severity, text, citations.
The text must be brief and grounded only in the tool result.
"""
    try:
        answer = _json_from_text(_complete(system_prompt, prompt, runtime_lm, max_tokens=900))
        text = str(answer.get("text", "")).strip()
        if text:
            if fallback and _looks_like_refusal(text):
                return fallback
            return text
    except Exception:
        pass
    return fallback or f"I used {tool} and grounded the response in its returned data."


def _looks_like_refusal(text: str) -> bool:
    q = text.lower()
    return q.startswith("refusal") or "cannot answer" in q or "unable to answer" in q


def _complete(system_prompt: str, prompt: str, runtime_lm: str, *, max_tokens: int) -> str:
    from openai import OpenAI

    model = os.environ.get("GEMMA_MODEL") or _model_for_openai(runtime_lm)
    client = OpenAI(
        api_key=os.environ["GEMMA_API_KEY"],
        base_url=os.environ.get("GEMMA_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def _tool_router_prompt(run_context: str | None) -> str:
    return f"""\
Available tools. Return exactly one JSON object with keys tool, args, reason.
Known components: {", ".join(c.value for c in ROW_ORDER)}.
Known runs: {", ".join(_KNOWN_RUNS)}.
Current run context: {run_context or "none"}.

Aliases:
- "dark twin" means run {_DARK_TWIN_RUN}.
- "apollo" means run {_APOLLO_RUN}.
- "fixed schedule" means run {_FIXED_RUN}.
- "dark twin graph", "dark twin plot", and "dark twin's components" mean all six components in run {_DARK_TWIN_RUN}.
- "component history", "plot history", "timeline", "graph", and "show history" mean plot_component_history.
- "compare Apollo and dark twin" means compare_runs with [{_APOLLO_RUN}, {_DARK_TWIN_RUN}].

Routing rules:
- direct health/status/value for one run+component -> query_historian
- why/cascade/explain rows -> late_interaction_search
- compare/across universes/runs -> compare_runs
- what if/counterfactual/replaced at hour -> run_counterfactual
- show/plot/history/timeline for a valid component -> plot_component_history
- unsupported component, unknown run, weather, stocks, sports, recipes, music -> REFUSAL

Tool schemas:
- query_historian: {{"run_id": str, "component": component, "time_range": [iso_start, iso_end]}}
- late_interaction_search: {{"query": str, "run_id": str|null, "top_k": int}}
- compare_runs: {{"run_ids": [str, ...], "metric": "avg_health"|"uptime_hours"|"failure_count"|"maintenance_count"}}
- run_counterfactual: {{"run_id": str, "branch_t": iso_datetime, "alternate_action": {{"action": str, "component_id": component}}}}
- plot_component_history: {{"run_id": str, "component": component}}
"""


def _normalize_args(
    tool: str, args: dict[str, Any], query: str, run_context: str | None
) -> dict[str, Any]:
    args = dict(args or {})
    run_id = _infer_run_id(query, run_context)
    component = _infer_component(query)
    if tool == "query_historian":
        if run_id:
            args["run_id"] = run_id
        if component:
            args["component"] = component.value
        args.setdefault("time_range", ["2000-01-01T00:00:00", "2100-01-01T00:00:00"])
        if args["time_range"] == ["start", "end"]:
            args["time_range"] = ["2000-01-01T00:00:00", "2100-01-01T00:00:00"]
    elif tool == "late_interaction_search":
        args.setdefault("query", query)
        args["run_id"] = run_id or args.get("run_id")
        args.setdefault("top_k", 5)
    elif tool == "compare_runs":
        run_ids = _infer_compare_run_ids(query, run_context)
        if run_ids:
            args["run_ids"] = run_ids
        args.setdefault("metric", "avg_health")
    elif tool == "run_counterfactual":
        if run_id:
            args["run_id"] = run_id
        if component:
            action = dict(args.get("alternate_action") or {})
            action.setdefault("action", "replace")
            action["component_id"] = component.value
            args["alternate_action"] = action
    elif tool == "plot_component_history":
        if run_id:
            args["run_id"] = run_id
        if component:
            args["component"] = component.value
    return args


def _infer_run_id(query: str, run_context: str | None) -> str | None:
    q = query.lower()
    if "apollo" in q:
        return _APOLLO_RUN
    if "fixed schedule" in q or re.search(r"\bfixed\b", q):
        return _FIXED_RUN
    if "dark twin" in q:
        return _DARK_TWIN_RUN
    for run in _KNOWN_RUNS:
        if run in query:
            return run
    return run_context


def _infer_component(query: str) -> ComponentId | None:
    q = query.lower()
    for component in ROW_ORDER:
        if component.value in q or component.value + "s" in q:
            return component
    if "bearing" in q:
        return ComponentId.MOTOR
    return None


def _wants_all_component_history(query: str) -> bool:
    q = query.lower()
    if "dark twin" in q and any(word in q for word in ("graph", "plot", "history", "timeline")):
        return True
    wants_plot = any(word in q for word in ("plot", "history", "timeline", "graph", "show me"))
    wants_all = "components" in q or "all six" in q or "all components" in q
    return wants_plot and wants_all


def _wants_run_comparison(query: str, run_context: str | None) -> bool:
    q = query.lower()
    if _wants_all_component_history(query):
        return False
    run_ids = _infer_compare_run_ids(query, run_context)
    comparison_word = any(word in q for word in ("compare", "versus", " vs ", "better", "worse", "outperform"))
    policy_why = "why" in q and any(word in q for word in ("better", "worse", "outperform"))
    return len(run_ids) >= 2 and (comparison_word or policy_why)


def _infer_compare_run_ids(query: str, run_context: str | None) -> list[str]:
    q = query.lower()
    run_ids: list[str] = []

    def add(run_id: str | None) -> None:
        if run_id and run_id not in run_ids:
            run_ids.append(run_id)

    for run in _KNOWN_RUNS:
        if run in query:
            add(run)
    if "apollo" in q or "ai policy" in q:
        add(_APOLLO_RUN)
    if "fixed schedule" in q or re.search(r"\bfixed\b", q):
        add(_FIXED_RUN)
    if "dark twin" in q or "no maintenance" in q or "no-maintenance" in q:
        add(_DARK_TWIN_RUN)
    if run_context and run_context in _KNOWN_RUNS:
        add(run_context)
    if len(run_ids) == 1 and any(word in q for word in ("compare", "versus", " vs ")):
        for run in (_DARK_TWIN_RUN, _FIXED_RUN, _APOLLO_RUN):
            add(run)
    return run_ids


def _infer_compare_metric(query: str) -> str:
    q = query.lower()
    if "uptime" in q or "downtime" in q:
        return "uptime_hours"
    if "failure" in q or "failed" in q or "fails" in q:
        return "failure_count"
    if "maintenance" in q or "intervention" in q:
        return "maintenance_count"
    return "avg_health"


def _compare_runs_fallback(query: str, args: dict[str, Any], result: Any) -> str:
    run_ids = list(args.get("run_ids") or [])
    metric = str(args.get("metric") or "avg_health")
    if isinstance(result, dict):
        values = ", ".join(f"{_run_label(run)}: {float(result[run]):.3f}" for run in run_ids if run in result)
    else:
        values = ""

    if not values:
        return "I compared the requested policy runs, but the historian did not return metric values."

    text = f"Using {metric}, the comparison is: {values}."
    q = query.lower()
    if "why" in q or "worse" in q or "better" in q:
        text += (
            " The policy difference is that Apollo is the adaptive AI policy, "
            "fixed schedule follows preplanned maintenance, and dark twin is the no-maintenance baseline."
        )
    return text


def _run_label(run_id: str) -> str:
    if run_id == _APOLLO_RUN:
        return "Apollo"
    if run_id == _FIXED_RUN:
        return "fixed schedule"
    if run_id == _DARK_TWIN_RUN:
        return "dark twin"
    return run_id


def _citations_from_tool_result(
    tool: str, args: dict[str, Any], result: Any, db_path: str
) -> list[Citation]:
    if tool in {"query_historian", "late_interaction_search"} and isinstance(result, list):
        return [_row_to_citation(row) for row in result[:2] + result[-2:]]
    if tool == "plot_component_history":
        try:
            return _citations_for_component(db_path, str(args["run_id"]), ComponentId(str(args["component"])))
        except Exception:
            return []
    return []


def _citations_for_component(db_path: str, run_id: str, component: ComponentId) -> list[Citation]:
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_id, component_id, t FROM component_states "
            "WHERE run_id=? AND component_id=? ORDER BY t ASC",
            (run_id, component.value),
        ).fetchall()
    if not rows:
        return []
    return [_row_to_citation(dict(rows[0])), _row_to_citation(dict(rows[-1]))]


def _row_to_citation(row: dict[str, Any]) -> Citation:
    ts = row.get("t") or row.get("timestamp")
    return Citation(
        run_id=str(row["run_id"]),
        component=ComponentId(str(row.get("component_id") or row.get("component"))),
        timestamp=datetime.fromisoformat(str(ts)),
    )


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    out: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for citation in citations:
        key = (citation.run_id, citation.component.value, citation.timestamp.isoformat())
        if key in seen:
            continue
        seen.add(key)
        out.append(citation)
    return out


def _citation_payload(citation: Citation) -> dict[str, str]:
    return {
        "run_id": citation.run_id,
        "component": citation.component.value,
        "timestamp": citation.timestamp.isoformat(),
    }


@contextmanager
def _historian_env(db_path: str):
    prior_path = os.environ.get("HISTORIAN_PATH")
    os.environ["HISTORIAN_PATH"] = db_path
    try:
        yield
    finally:
        if prior_path is None:
            os.environ.pop("HISTORIAN_PATH", None)
        else:
            os.environ["HISTORIAN_PATH"] = prior_path


async def _stream_refusal(reason: str, trace_url: str) -> AsyncIterator[dict]:
    text = REFUSAL_TEMPLATE.format(summarized_query=f"'{reason[:120]}'")
    for token in _tokenize(text):
        yield {"type": "text-delta", "payload": {"token": token}}
    yield {"type": "done", "payload": {"trace_url": trace_url}}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\S+\s*|\s+", text)


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    decoder = json.JSONDecoder()
    first: dict[str, Any] | None = None
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[i:])
            if isinstance(obj, dict):
                if first is None:
                    first = obj
                if "tool" in obj and "args" in obj:
                    return obj
        except json.JSONDecodeError:
            continue
    if first is not None:
        return first
    raise ValueError(f"no JSON object in model output: {text[:300]}")


def _model_for_openai(runtime_lm: str) -> str:
    if runtime_lm.startswith("models/"):
        return runtime_lm
    return "models/gemma-4-31b-it"


def _trace_url_for(query: str) -> str:
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    trace_id = uuid.uuid5(uuid.NAMESPACE_URL, f"apollo|{query}").hex
    return f"{host}/trace/{trace_id}"
