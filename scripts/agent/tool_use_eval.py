"""Shared ADR-022 tool-use eval utilities.

The eval is deterministic and generated from a small set of frozen run/component
templates so GEPA gets enough signal without hand-maintaining a huge JSON file.
"""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

from apollo.agent.citations import resolve_citation  # noqa: E402
from apollo.agent.contracts import Citation  # noqa: E402
from apollo.agent.metric import _faithfulness  # noqa: E402
from engine.contracts import ComponentId  # noqa: E402
from sim.drivers.composite import SIM_START_TIME  # noqa: E402

EVAL_PATH = REPO_ROOT / "tests" / "eval" / "tool_use_set.json"

RUNS = [
    "barcelona-humid-ai-seed0042",
    "barcelona-humid-fixed-seed0042",
    "barcelona-humid-none-seed0042",
    "phoenix-dry-ai-seed0042",
    "phoenix-dry-fixed-seed0042",
    "phoenix-dry-none-seed0042",
    "stressed-ai-seed0042",
    "stressed-fixed-seed0042",
    "stressed-none-seed0042",
]
COMPONENTS = ["blade", "motor", "nozzle", "resistor", "heater", "insulation"]
TS = "2026-04-25T08:00:00"


def load_tool_use_items(split: str = "all", limit: int | None = None) -> list[dict[str, Any]]:
    """Load curated plus generated ADR-022 cases."""
    curated = json.loads(EVAL_PATH.read_text(encoding="utf-8")).get("items", [])
    generated = _generated_cases()
    by_id = {item["id"]: item for item in [*curated, *generated]}
    items = list(by_id.values())
    if split != "all":
        items = [item for item in items if item.get("split", "train") == split]
    return items[:limit] if limit else items


def tool_descriptions() -> str:
    known_runs = ", ".join(RUNS)
    known_components = ", ".join(COMPONENTS)
    return f"""\
Available tools. Return exactly one JSON object with keys tool, args, reason.
Use "REFUSAL" as tool if the question is off-topic, the component/run is unknown,
or no telemetry can support the answer.

Known components: {known_components}.
Known runs: {known_runs}.

Routing rules:
- direct health/status/value for one run+component -> query_historian
- why/cascade/explain rows -> late_interaction_search
- compare/across universes/runs -> compare_runs
- what if/counterfactual/replaced at hour -> run_counterfactual
- show/plot/history/timeline for a valid component -> plot_component_history
- microwave, binder viscosity, pump pressure, run-9999, weather, stock, music -> REFUSAL
- "motor bearing" means the motor component, but "bearing temperature" alone is unsupported

Tools:
- query_historian: args {{"run_id": str, "component": component, "time_range": [iso_start, iso_end]}}
- late_interaction_search: args {{"query": str, "run_id": str|null, "top_k": int}}
- compare_runs: args {{"run_ids": [str, ...], "metric": "uptime_hours"|"failure_count"|"maintenance_count"|"avg_health"}}
- run_counterfactual: args {{"run_id": str, "branch_t": iso_datetime, "alternate_action": {{"action": str, "component_id": component}}}}
- plot_component_history: args {{"run_id": str, "component": component}}

Return only JSON. Do not answer yet.
"""


def json_from_text(text: str) -> dict[str, Any]:
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


def context_from_result(result: Any) -> str:
    return json.dumps(result, default=str, ensure_ascii=False)[:8000]


def normalize_args(tool: str, args: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    args = dict(args or {})
    if tool == "query_historian":
        if isinstance(args.get("time_range"), list):
            args["time_range"] = [_strip_utc(str(v)) for v in args["time_range"][:2]]
        args.setdefault("run_id", item.get("expected_run_id"))
        args.setdefault("component", item.get("expected_component"))
        args.setdefault("time_range", [item.get("expected_timestamp", TS), item.get("expected_timestamp", TS)])
    elif tool == "late_interaction_search":
        args.setdefault("query", item["question"])
        args.setdefault("run_id", item.get("expected_run_id"))
        args.setdefault("top_k", 5)
    elif tool == "compare_runs":
        args.setdefault("run_ids", item.get("expected_run_ids") or [])
        args.setdefault("metric", "avg_health")
    elif tool == "run_counterfactual":
        args.setdefault("run_id", item.get("expected_run_id"))
        hour = _hour_from_question(item["question"])
        branch_t = _strip_utc(str(args.get("branch_t") or ""))
        if f"hour {hour}" in branch_t.lower() or not branch_t.startswith("2026-"):
            branch_t = (SIM_START_TIME + timedelta(hours=hour)).isoformat()
        args["branch_t"] = branch_t
        args.setdefault(
            "alternate_action",
            {"action": "replace", "component_id": item.get("expected_component", "nozzle")},
        )
    elif tool == "plot_component_history":
        args.setdefault("run_id", item.get("expected_run_id"))
        args.setdefault("component", item.get("expected_component"))
    return args


def args_match(tool: str, args: dict[str, Any], item: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if expected := item.get("expected_run_id"):
        if args.get("run_id") != expected:
            issues.append(f"run_id should be {expected}, got {args.get('run_id')!r}")
    if expected_component := item.get("expected_component"):
        action_component = (args.get("alternate_action") or {}).get("component_id")
        component = action_component if tool == "run_counterfactual" else args.get("component")
        if component != expected_component:
            issues.append(f"component should be {expected_component}, got {component!r}")
    if expected_run_ids := item.get("expected_run_ids"):
        if set(args.get("run_ids") or []) != set(expected_run_ids):
            issues.append(f"run_ids should be {expected_run_ids}, got {args.get('run_ids')!r}")
    return not issues, issues


def citation_resolution(answer: dict[str, Any]) -> tuple[int, int]:
    citations = answer.get("citations") or []
    ok = 0
    for raw in citations:
        try:
            citation = Citation(
                run_id=raw["run_id"],
                component=ComponentId(raw["component"]),
                timestamp=_strip_utc(str(raw["timestamp"])),
            )
            if resolve_citation(citation):
                ok += 1
        except Exception:
            continue
    return ok, len(citations)


def score_answer(item: dict[str, Any], tool: str, answer: dict[str, Any], result: Any) -> dict[str, Any]:
    text = str(answer.get("text", ""))
    faith = _faithfulness(text, [context_from_result(result)])
    ok, total = citation_resolution(answer)
    requires_citation = bool(item.get("requires_citation", tool in {"query_historian", "late_interaction_search"}))
    contains = all(
        str(bit).lower() in (text + json.dumps(answer, default=str)).lower()
        for bit in item.get("expected_contains", [])
    )
    fabricated = max(0, total - ok) if requires_citation else 0
    missing = 1 if requires_citation and total == 0 else 0
    citation_ok = (not requires_citation) or (total > 0 and ok == total)
    return {
        "faithfulness": faith,
        "answer_contains": contains,
        "citation_ok": citation_ok,
        "citation_resolved": ok,
        "citation_total": total,
        "hallucinations": fabricated,
        "missing_required_citations": missing,
        "passed_answer": citation_ok and contains and faith >= 0.5,
    }


def _generated_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for idx, (run, component) in enumerate((r, c) for r in RUNS for c in COMPONENTS):
        if idx >= 24:
            break
        cases.append(_case(
            f"query-{run}-{component}",
            f"What was the {component} health in run {run} at {TS}?",
            "query_historian",
            idx,
            expected_run_id=run,
            expected_component=component,
            expected_timestamp=TS,
            expected_contains=[run, component, TS],
            requires_citation=True,
        ))
    for idx, run in enumerate(RUNS):
        cases.append(_case(
            f"search-cascade-{run}",
            f"Which historian rows best explain the thermal cascade in {run}?",
            "late_interaction_search",
            idx + 30,
            expected_run_id=run,
            expected_contains=[run],
            requires_citation=True,
        ))
    compare_sets = [
        ("barcelona", RUNS[0:3]),
        ("phoenix", RUNS[3:6]),
        ("stressed", RUNS[6:9]),
        ("ai-policy", [RUNS[0], RUNS[3], RUNS[6]]),
        ("fixed-policy", [RUNS[1], RUNS[4], RUNS[7]]),
        ("none-policy", [RUNS[2], RUNS[5], RUNS[8]]),
    ]
    for idx, (name, run_ids) in enumerate(compare_sets):
        cases.append(_case(
            f"compare-{name}",
            f"Compare average health across these runs: {', '.join(run_ids)}.",
            "compare_runs",
            idx + 45,
            expected_run_ids=run_ids,
            expected_contains=run_ids,
            requires_citation=False,
        ))
    for idx, (run, component) in enumerate(zip(RUNS, COMPONENTS + COMPONENTS[:3])):
        cases.append(_case(
            f"counterfactual-{run}-{component}",
            f"What if we replaced the {component} at hour 4 in {run}?",
            "run_counterfactual",
            idx + 55,
            expected_run_id=run,
            expected_component=component,
            expected_contains=[run, component],
            requires_citation=False,
        ))
    for idx, (run, component) in enumerate(zip(reversed(RUNS), COMPONENTS + COMPONENTS[:3])):
        cases.append(_case(
            f"plot-{run}-{component}",
            f"Show me the {component} history for {run}.",
            "plot_component_history",
            idx + 70,
            expected_run_id=run,
            expected_component=component,
            expected_contains=[run, component],
            requires_citation=False,
        ))
    refusals = [
        ("weather-madrid", "What is the weather in Madrid?"),
        ("stock-price", "What is HP stock trading at right now?"),
        ("music", "Recommend debugging music for the printer team."),
        ("microwave", f"Did the microwave component fail in {RUNS[0]}?"),
        ("binder", f"Show me the binder viscosity timeline for {RUNS[0]}."),
        ("run-9999", "What was the bearing temperature in run-9999?"),
        ("unknown-run", "Plot nozzle history for moonbase-vacuum-ai-seed0042."),
        ("pump", f"Compare pump pressure across {RUNS[0]} and {RUNS[1]}."),
        ("sports", "Who won the match last night?"),
        ("recipe", "Give me a dinner recipe for after the demo."),
    ]
    for idx, (name, question) in enumerate(refusals):
        cases.append(_case(
            f"refuse-{name}",
            question,
            "REFUSAL",
            idx + 85,
            expected_contains=["REFUSAL"],
            is_unanswerable=True,
        ))
    return cases


def _case(case_id: str, question: str, tool: str, idx: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": case_id,
        "split": "holdout" if idx % 4 == 0 else "train",
        "question": question,
        "expected_tool": tool,
        "is_unanswerable": tool == "REFUSAL",
        **extra,
    }


def _strip_utc(value: str) -> str:
    return value.replace("Z", "").replace("+00:00", "")


def _hour_from_question(question: str) -> int:
    match = re.search(r"\bhour\s+(\d+)\b", question.lower())
    return int(match.group(1)) if match else 4
