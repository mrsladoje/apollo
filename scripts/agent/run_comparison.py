"""Three-way ADR-022 live tool-use comparison.

The harness calls live models, forces one Apollo tool or REFUSAL, executes the
tool, asks for a grounded final answer, and reports train/holdout metrics.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from apollo.agent.tools.registry import ToolError, invoke  # noqa: E402
from scripts.agent.tool_use_eval import (  # noqa: E402
    args_match,
    context_from_result,
    json_from_text,
    load_tool_use_items,
    normalize_args,
    score_answer,
    tool_descriptions,
)

RESULTS_PATH = REPO_ROOT / "docs" / "eval" / "comparison_results.json"
SEED_PROMPT = REPO_ROOT / "src" / "apollo" / "agent" / "prompts" / "system.md"
GEPA_PROMPT = REPO_ROOT / "config" / "agent.system_prompt.gepa.txt"


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


def _select_tool(client: ModelClient, item: dict[str, Any]) -> dict[str, Any]:
    prompt = tool_descriptions() + "\nQuestion: " + item["question"] + "\nJSON:"
    return json_from_text(client.complete(prompt, max_tokens=500))


def _answer_from_tool(
    client: ModelClient, item: dict[str, Any], tool: str, args: dict[str, Any], result: Any
) -> dict[str, Any]:
    prompt = f"""\
Question: {item['question']}
Tool used: {tool}
Tool args: {json.dumps(args, default=str)}
Tool result/context:
{context_from_result(result)}

Return only JSON with:
{{
  "severity": "INFO"|"WARNING"|"CRITICAL"|"REFUSAL",
  "text": "brief answer grounded only in the tool result",
  "citations": [{{"run_id": "...", "component": "...", "timestamp": "..."}}]
}}
For query_historian or late_interaction_search answers include at least one citation triple from the tool result.
For compare_runs, run_counterfactual, and plot_component_history, cite if the tool result contains citation-like rows; otherwise answer from the structured tool output.
"""
    return json_from_text(client.complete(prompt, max_tokens=900))


def _eval(client: ModelClient, items: list[dict[str, Any]]) -> dict[str, Any]:
    counters = {
        "passed": 0,
        "tool_correct": 0,
        "valid_args": 0,
        "arg_match": 0,
        "answer_contains": 0,
        "hallucinations": 0,
        "missing_required_citations": 0,
        "citation_total": 0,
        "citation_resolved": 0,
        "refusals_correct": 0,
        "refusals_total": 0,
    }
    faiths: list[float] = []
    latencies: list[float] = []
    per_item: list[dict[str, Any]] = []

    for item in items:
        t0 = time.perf_counter()
        expected_tool = item["expected_tool"]
        row: dict[str, Any] = {"id": item["id"], "split": item.get("split"), "expected_tool": expected_tool}
        try:
            selected = _select_tool(client, item)
            tool = str(selected.get("tool", "")).strip()
            row["selected_tool"] = tool
            if tool == expected_tool:
                counters["tool_correct"] += 1

            if item["is_unanswerable"]:
                counters["refusals_total"] += 1
                if tool == "REFUSAL":
                    counters["refusals_correct"] += 1
                    counters["valid_args"] += 1
                    counters["arg_match"] += 1
                    counters["answer_contains"] += 1
                    counters["passed"] += 1
                    faiths.append(1.0)
                    row["passed"] = True
                else:
                    row["passed"] = False
                continue

            if tool == "REFUSAL":
                row["passed"] = False
                continue

            args = normalize_args(tool, selected.get("args") or {}, item)
            row["args"] = args
            matched, arg_issues = args_match(tool, args, item)
            if matched:
                counters["arg_match"] += 1
            else:
                row["arg_issues"] = arg_issues

            try:
                result = invoke(tool, args)
                counters["valid_args"] += 1
            except ToolError as exc:
                row["error"] = str(exc)
                row["passed"] = False
                continue

            answer = _answer_from_tool(client, item, tool, args, result)
            answer_score = score_answer(item, tool, answer, result)
            faiths.append(float(answer_score["faithfulness"]))
            counters["citation_total"] += int(answer_score["citation_total"])
            counters["citation_resolved"] += int(answer_score["citation_resolved"])
            counters["hallucinations"] += int(answer_score["hallucinations"])
            counters["missing_required_citations"] += int(answer_score["missing_required_citations"])
            if answer_score["answer_contains"]:
                counters["answer_contains"] += 1

            passed = tool == expected_tool and matched and bool(answer_score["passed_answer"])
            if passed:
                counters["passed"] += 1
            row.update(
                {
                    "faithfulness": round(float(answer_score["faithfulness"]), 3),
                    "citations_resolved": f"{answer_score['citation_resolved']}/{answer_score['citation_total']}",
                    "passed": passed,
                }
            )
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)
            row["passed"] = False
        finally:
            latencies.append(time.perf_counter() - t0)
            per_item.append(row)

    n = len(items)
    return {
        "n": n,
        "pass_rate": _rate(counters["passed"], n),
        "tool_accuracy": _rate(counters["tool_correct"], n),
        "valid_tool_args": _rate(counters["valid_args"], n),
        "arg_match_rate": _rate(counters["arg_match"], n),
        "answer_contains_rate": _rate(counters["answer_contains"], n),
        "faithfulness_avg": round(sum(faiths) / len(faiths), 3) if faiths else 0.0,
        "hallucination_count": counters["hallucinations"],
        "missing_required_citation_count": counters["missing_required_citations"],
        "citation_resolve_rate": _rate(counters["citation_resolved"], counters["citation_total"]),
        "refusals_correct": counters["refusals_correct"],
        "refusals_total": counters["refusals_total"],
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


def run(
    split: str = "holdout",
    seeds: int = 1,
    limit: int | None = None,
    configs: tuple[str, ...] = ("vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"),
    parallelism: int = 1,
    write: bool = True,
) -> dict[str, Any]:
    items = load_tool_use_items(split=split, limit=limit)
    seed_results: dict[str, list[dict[str, Any]]] = {name: [] for name in configs}

    jobs = [(name, seed) for name in configs for seed in range(seeds)]
    if parallelism > 1 and len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=parallelism) as pool:
            futures = {
                pool.submit(_eval_config_seed, name, seed, items): (name, seed)
                for name, seed in jobs
            }
            for future in as_completed(futures):
                name, _seed = futures[future]
                seed_results[name].append(future.result())
    else:
        for name, seed in jobs:
            seed_results[name].append(_eval_config_seed(name, seed, items))

    rows: list[dict[str, Any]] = []
    for name in configs:
        seed_rows = sorted(seed_results[name], key=lambda row: int(row["seed"]))
        aggregate = _aggregate(seed_rows)
        aggregate["config"] = name
        aggregate["runs"] = seed_rows
        rows.append(aggregate)
    payload = {
        "eval": "tests/eval/tool_use_set.json",
        "split": split,
        "n_items": len(items),
        "seeds": seeds,
        "parallelism": parallelism,
        "rows": rows,
    }
    if write:
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _eval_config_seed(name: str, seed: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = _eval(_client(name), items)
    metrics["seed"] = seed
    return metrics


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
    if "pass_rate_mean" not in gepa:
        print("[check] stale comparison schema; rerun scripts/agent/run_comparison.py first.", file=sys.stderr)
        return 1
    if gepa["pass_rate_mean"] < gemma["pass_rate_mean"]:
        print(
            f"[check] GEPA-Gemma pass rate {gepa['pass_rate_mean']:.3f} below vanilla Gemma {gemma['pass_rate_mean']:.3f}",
            file=sys.stderr,
        )
        return 1
    diff_pp = (opus["pass_rate_mean"] - gepa["pass_rate_mean"]) * 100.0
    if diff_pp > 2.0:
        print(
            f"[check] GEPA-Gemma pass rate {gepa['pass_rate_mean']:.3f} > 2pp below Opus {opus['pass_rate_mean']:.3f}",
            file=sys.stderr,
        )
        return 1
    if gepa["hallucination_count_mean"] != 0:
        print("[check] GEPA-Gemma row had hallucinations", file=sys.stderr)
        return 1
    print(
        "[check] OK - "
        f"Opus {opus['pass_rate_mean']:.3f}, "
        f"Gemma {gemma['pass_rate_mean']:.3f}, "
        f"GEPA-Gemma {gepa['pass_rate_mean']:.3f}, "
        f"Opus delta {diff_pp:+.2f}pp"
    )
    return 0


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "pass_rate",
        "tool_accuracy",
        "valid_tool_args",
        "arg_match_rate",
        "answer_contains_rate",
        "faithfulness_avg",
        "hallucination_count",
        "missing_required_citation_count",
        "citation_resolve_rate",
        "latency_avg_s",
    ]
    out: dict[str, Any] = {}
    for key in keys:
        vals = [float(row[key]) for row in rows]
        out[f"{key}_mean"] = round(sum(vals) / len(vals), 3)
        out[f"{key}_stdev"] = round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0
    return out


def _rate(num: int, den: int) -> float:
    return round(num / den, 3) if den else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--split", choices=["train", "holdout", "all"], default="holdout")
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--parallelism",
        type=int,
        default=int(os.environ.get("COMPARISON_PARALLELISM", "1")),
        help="Parallel config/seed workers for live comparison runs.",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=["vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"],
        choices=["vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"],
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    print(
        json.dumps(
            run(
                split=args.split,
                seeds=args.seeds,
                limit=args.limit,
                configs=tuple(args.configs),
                parallelism=args.parallelism,
                write=not args.no_write,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
