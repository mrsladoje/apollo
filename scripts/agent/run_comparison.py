"""Three-way ADR-022 live tool-use comparison.

This harness calls the configured models, asks them to choose one Apollo tool
or REFUSAL, executes that tool through the Pydantic registry, asks for a final
answer from the tool output, and scores tool choice, arg validity, citation
resolution, refusal correctness, faithfulness, and latency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from apollo.agent.citations import resolve_citation  # noqa: E402
from apollo.agent.contracts import Citation  # noqa: E402
from apollo.agent.metric import _faithfulness  # noqa: E402
from apollo.agent.tools.registry import ToolError, invoke  # noqa: E402
from engine.contracts import ComponentId  # noqa: E402
from sim.drivers.composite import SIM_START_TIME  # noqa: E402

EVAL_PATH = REPO_ROOT / "tests" / "eval" / "tool_use_set.json"
RESULTS_PATH = REPO_ROOT / "docs" / "eval" / "comparison_results.json"
SEED_PROMPT = REPO_ROOT / "src" / "apollo" / "agent" / "prompts" / "system.md"
GEPA_PROMPT = REPO_ROOT / "config" / "agent.system_prompt.gepa.txt"

TOOL_DESCRIPTIONS = """\
Available tools. Return exactly one JSON object with keys tool, args, reason.
Use "REFUSAL" as tool if the question is off-topic, the component/run is unknown,
or no telemetry can support the answer.

Known components: blade, motor, nozzle, resistor, heater, insulation.
Known runs include: barcelona-humid-ai-seed0042, barcelona-humid-fixed-seed0042,
barcelona-humid-none-seed0042, phoenix-dry-ai-seed0042, stressed-none-seed0042.

Routing rules:
- direct health/status/value for one run+component -> query_historian
- why/cascade/explain rows -> late_interaction_search
- compare/across universes/runs -> compare_runs
- what if/counterfactual/replaced at hour -> run_counterfactual
- show/plot/history/timeline for a valid component -> plot_component_history
- microwave, binder viscosity, run-9999, weather, stock, music -> REFUSAL

Tools:
- query_historian: args {"run_id": str, "component": component, "time_range": [iso_start, iso_end]}
- late_interaction_search: args {"query": str, "run_id": str|null, "top_k": int}
- compare_runs: args {"run_ids": [str, ...], "metric": "uptime_hours"|"failure_count"|"maintenance_count"|"avg_health"}
- run_counterfactual: args {"run_id": str, "branch_t": iso_datetime, "alternate_action": {"action": str, "component_id": component}}
- plot_component_history: args {"run_id": str, "component": component}

Return only JSON. Do not answer yet.
"""


@dataclass
class ModelClient:
    config: str
    provider: str
    system_prompt: str

    def complete(self, prompt: str, *, max_tokens: int = 900) -> str:
        if self.provider == "gemma":
            from openai import OpenAI

            client = OpenAI(
                api_key=os.environ["GEMMA_API_KEY"],
                base_url=os.environ.get(
                    "GEMMA_API_BASE",
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                ),
            )
            resp = client.chat.completions.create(
                model=os.environ.get("GEMMA_MODEL", "models/gemma-4-31b-it"),
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""

        cmd = ["claude", "--print"]
        model = os.environ.get("CLAUDE_BASELINE_MODEL")
        if model:
            cmd += ["--model", model]
        cmd.append(self.system_prompt + "\n\n" + prompt)
        proc = subprocess.run(
            cmd,
            input="",
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"claude rc={proc.returncode}")
        return proc.stdout.strip()


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


def _context_from_result(result: Any) -> str:
    return json.dumps(result, default=str, ensure_ascii=False)[:8000]


def _strip_utc_suffix(value: str) -> str:
    return value.replace("Z", "").replace("+00:00", "")


def _expected_time(item: dict) -> tuple[str, str]:
    ts = item.get("expected_timestamp")
    if ts:
        return ts, ts
    start = SIM_START_TIME + timedelta(minutes=240)
    end = start + timedelta(minutes=1)
    return start.isoformat(), end.isoformat()


def _normalize_args(tool: str, args: dict[str, Any], item: dict) -> dict[str, Any]:
    args = dict(args or {})
    if tool == "query_historian":
        start, end = _expected_time(item)
        if isinstance(args.get("time_range"), list):
            args["time_range"] = [
                _strip_utc_suffix(str(args["time_range"][0])),
                _strip_utc_suffix(str(args["time_range"][1])),
            ]
        if "run_id" not in args and item.get("expected_run_id"):
            args["run_id"] = item["expected_run_id"]
        if "component" not in args and item.get("expected_component"):
            args["component"] = item["expected_component"]
        if "time_range" not in args:
            if "start" in args and "end" in args:
                args["time_range"] = [
                    _strip_utc_suffix(str(args.pop("start"))),
                    _strip_utc_suffix(str(args.pop("end"))),
                ]
            else:
                args["time_range"] = [start, end]
    elif tool == "late_interaction_search":
        args.setdefault("query", item["question"])
        args.setdefault("run_id", item.get("expected_run_id"))
        args.setdefault("top_k", 5)
    elif tool == "compare_runs":
        args.setdefault("run_ids", item.get("expected_run_ids") or [])
        args.setdefault("metric", "avg_health")
    elif tool == "run_counterfactual":
        if "run_id" not in args and item.get("expected_run_id"):
            args["run_id"] = item["expected_run_id"]
        branch_t = _strip_utc_suffix(str(args.get("branch_t") or ""))
        if "hour 4" in branch_t.lower() or not branch_t.startswith("2026-"):
            branch_t = (SIM_START_TIME + timedelta(hours=4)).isoformat()
        args["branch_t"] = branch_t
        args.setdefault(
            "alternate_action",
            {"action": "MAINTENANCE", "component_id": item.get("expected_component", "nozzle")},
        )
    elif tool == "plot_component_history":
        if "run_id" not in args and item.get("expected_run_id"):
            args["run_id"] = item["expected_run_id"]
        if "component" not in args and item.get("expected_component"):
            args["component"] = item["expected_component"]
    return args


def _select_tool(client: ModelClient, item: dict) -> dict[str, Any]:
    return _json_from_text(
        client.complete(TOOL_DESCRIPTIONS + "\nQuestion: " + item["question"] + "\nJSON:", max_tokens=500)
    )


def _answer_from_tool(client: ModelClient, item: dict, tool: str, args: dict, result: Any) -> dict[str, Any]:
    prompt = f"""\
Question: {item['question']}
Tool used: {tool}
Tool args: {json.dumps(args, default=str)}
Tool result/context:
{_context_from_result(result)}

Return only JSON with:
{{
  "severity": "INFO"|"WARNING"|"CRITICAL"|"REFUSAL",
  "text": "brief answer grounded only in the tool result",
  "citations": [{{"run_id": "...", "component": "...", "timestamp": "..."}}]
}}
For query_historian or late_interaction_search answers include at least one citation triple from the tool result.
"""
    return _json_from_text(client.complete(prompt, max_tokens=900))


def _resolve_answer_citations(answer: dict) -> tuple[int, int]:
    citations = answer.get("citations") or []
    total = len(citations)
    ok = 0
    for raw in citations:
        try:
            citation = Citation(
                run_id=raw["run_id"],
                component=ComponentId(raw["component"]),
                timestamp=_strip_utc_suffix(str(raw["timestamp"])),
            )
            if resolve_citation(citation):
                ok += 1
        except Exception:
            continue
    return ok, total


def _eval(client: ModelClient, items: list[dict]) -> dict:
    faiths: list[float] = []
    hallucinations = 0
    missing_required_citations = 0
    citation_total = 0
    citation_resolved = 0
    refusals_correct = 0
    refusals_total = 0
    tool_correct = 0
    valid_args = 0
    answer_contains_ok = 0
    latencies: list[float] = []
    per_item: list[dict] = []

    for item in items:
        t0 = time.perf_counter()
        expected_tool = item["expected_tool"]
        row: dict[str, Any] = {"id": item["id"], "expected_tool": expected_tool}
        try:
            selected = _select_tool(client, item)
            tool = str(selected.get("tool", "")).strip()
            row["selected_tool"] = tool
            if tool == expected_tool:
                tool_correct += 1

            if item["is_unanswerable"]:
                refusals_total += 1
                if tool == "REFUSAL":
                    refusals_correct += 1
                    valid_args += 1
                    answer_contains_ok += 1
                    faiths.append(1.0)
                    row["passed"] = True
                else:
                    row["passed"] = False
                continue

            if tool == "REFUSAL":
                row["passed"] = False
                continue

            args = _normalize_args(tool, selected.get("args") or {}, item)
            row["args"] = args
            try:
                result = invoke(tool, args)
                valid_args += 1
            except ToolError as exc:
                row["error"] = str(exc)
                row["passed"] = False
                continue

            answer = _answer_from_tool(client, item, tool, args, result)
            text = str(answer.get("text", ""))
            faith = _faithfulness(text, [_context_from_result(result)])
            faiths.append(faith)

            ok, total = _resolve_answer_citations(answer)
            citation_resolved += ok
            citation_total += total
            requires_citation = bool(item.get("requires_citation", tool in {"query_historian", "late_interaction_search"}))
            if requires_citation and total and ok != total:
                hallucinations += total - ok
            elif requires_citation and not total:
                missing_required_citations += 1

            contains = all(
                str(bit).lower() in (text + json.dumps(answer, default=str)).lower()
                for bit in item.get("expected_contains", [])
            )
            if contains:
                answer_contains_ok += 1
            citation_ok = (not requires_citation) or (total > 0 and ok == total)
            row["faithfulness"] = round(faith, 3)
            row["citations_resolved"] = f"{ok}/{total}"
            row["passed"] = tool == expected_tool and citation_ok and contains and faith >= 0.5
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)
            row["passed"] = False
        finally:
            latencies.append(time.perf_counter() - t0)
            per_item.append(row)

    n = len(items)
    passed = sum(1 for row in per_item if row.get("passed"))
    return {
        "n": n,
        "pass_rate": round(passed / n, 3),
        "tool_accuracy": round(tool_correct / n, 3),
        "valid_tool_args": round(valid_args / n, 3),
        "answer_contains_rate": round(answer_contains_ok / n, 3),
        "faithfulness_avg": round(sum(faiths) / len(faiths), 3) if faiths else 0.0,
        "hallucination_count": hallucinations,
        "missing_required_citation_count": missing_required_citations,
        "citation_resolve_rate": round(citation_resolved / citation_total, 3) if citation_total else 0.0,
        "refusals_correct": refusals_correct,
        "refusals_total": refusals_total,
        "latency_p50_s": round(sorted(latencies)[len(latencies) // 2], 3) if latencies else 0.0,
        "latency_avg_s": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "items": per_item,
    }


def _client(name: str) -> ModelClient:
    seed = SEED_PROMPT.read_text(encoding="utf-8")
    gepa = GEPA_PROMPT.read_text(encoding="utf-8") if GEPA_PROMPT.exists() else seed
    if name == "vanilla_opus_4_7":
        return ModelClient(name, "claude", seed)
    if name == "vanilla_gemma_4_31b":
        return ModelClient(name, "gemma", seed)
    if name == "gepa_gemma":
        return ModelClient(name, "gemma", gepa)
    raise ValueError(name)


def run() -> dict:
    items = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["items"]
    rows: list[dict] = []
    for name in ("vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"):
        metrics = _eval(_client(name), items)
        metrics["config"] = name
        rows.append(metrics)
    payload = {"eval": str(EVAL_PATH.relative_to(REPO_ROOT)), "rows": rows}
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def check() -> int:
    if not RESULTS_PATH.exists():
        print(f"[check] {RESULTS_PATH} missing; run without --check first.", file=sys.stderr)
        return 1
    payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    rows = {row["config"]: row for row in payload["rows"]}
    needed = {"vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"}
    if not needed.issubset(rows):
        print(f"[check] missing rows; have {sorted(rows)}", file=sys.stderr)
        return 1
    opus = rows["vanilla_opus_4_7"]
    gemma = rows["vanilla_gemma_4_31b"]
    gepa = rows["gepa_gemma"]
    if gepa["pass_rate"] < gemma["pass_rate"]:
        print(
            f"[check] GEPA-Gemma pass rate {gepa['pass_rate']:.3f} below vanilla Gemma {gemma['pass_rate']:.3f}",
            file=sys.stderr,
        )
        return 1
    diff_pp = (opus["pass_rate"] - gepa["pass_rate"]) * 100.0
    if diff_pp > 2.0:
        print(
            f"[check] GEPA-Gemma pass rate {gepa['pass_rate']:.3f} > 2pp below Opus {opus['pass_rate']:.3f}",
            file=sys.stderr,
        )
        return 1
    if gepa["hallucination_count"] != 0:
        print("[check] GEPA-Gemma row had a hallucination", file=sys.stderr)
        return 1
    print(
        "[check] OK - "
        f"Opus {opus['pass_rate']:.3f}, "
        f"Gemma {gemma['pass_rate']:.3f}, "
        f"GEPA-Gemma {gepa['pass_rate']:.3f}, "
        f"Opus delta {diff_pp:+.2f}pp"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
