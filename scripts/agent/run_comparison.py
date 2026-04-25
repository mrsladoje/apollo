"""Three-way grounding eval comparison (PLAN-C §14a, FR-W.11).

Runs the FR-W.9 eval set against three configurations:
  1. Vanilla Opus 4.7 — Apollo loop with the seed prompt (Claude CLI runtime)
  2. Vanilla Gemma 4 31B — Apollo loop on Gemma with the seed prompt
  3. GEPA-Gemma — Apollo loop on Gemma with the compiled prompt

Logs to ``docs/eval/comparison_results.json``. Pass gate: GEPA-Gemma's
faithfulness within 2pp of Opus 4.7; hallucination = 0 on both rows.

Use ``--check`` to assert the pass gate against an existing results file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from apollo.agent.citations import resolve_citation  # noqa: E402
from apollo.agent.contracts import ApolloResponse  # noqa: E402
from apollo.agent.loop import AgentLoop  # noqa: E402
from apollo.agent.metric import _faithfulness  # noqa: E402

EVAL_PATH = REPO_ROOT / "tests" / "eval" / "grounding_set.json"
RESULTS_PATH = REPO_ROOT / "docs" / "eval" / "comparison_results.json"
HISTORIAN = REPO_ROOT / "historian.db"


def _eval(loop: AgentLoop, items: list[dict]) -> dict:
    faiths: list[float] = []
    hallucinations = 0
    refusals_correct = 0
    refusals_total = 0
    n_correct_severity = 0

    for item in items:
        resp: ApolloResponse = loop.answer(item["question"], item.get("expected_run_id"))
        if item["is_unanswerable"]:
            refusals_total += 1
            if resp.severity == "REFUSAL":
                refusals_correct += 1
        else:
            faith = _faithfulness(resp.text, item.get("contexts", []))
            faiths.append(faith)
        for c in resp.citations:
            if not resolve_citation(c):
                hallucinations += 1
        if resp.severity == item.get("expected_severity") or resp.severity == "REFUSAL" and item.get("is_unanswerable"):
            n_correct_severity += 1

    avg_faith = sum(faiths) / len(faiths) if faiths else 0.0
    return {
        "n": len(items),
        "n_grounded": sum(1 for i in items if not i["is_unanswerable"]),
        "n_unanswerable": refusals_total,
        "faithfulness_avg": round(avg_faith, 3),
        "hallucination_count": hallucinations,
        "refusals_correct": refusals_correct,
        "refusals_total": refusals_total,
    }


def _config_loop(name: str) -> AgentLoop:
    """Return an ``AgentLoop`` configured for the named comparison row."""
    if name == "vanilla_opus_4_7":
        os.environ["APOLLO_RUNTIME_LM"] = "claude_cli/opus-4-7"
        os.environ["APOLLO_PROMPT_VARIANT"] = "seed"
    elif name == "vanilla_gemma_4_31b":
        os.environ["APOLLO_RUNTIME_LM"] = "google/gemma-4-31B-it"
        os.environ["APOLLO_PROMPT_VARIANT"] = "seed"
    elif name == "gepa_gemma":
        os.environ["APOLLO_RUNTIME_LM"] = "google/gemma-4-31B-it"
        os.environ["APOLLO_PROMPT_VARIANT"] = "gepa"
    else:
        raise ValueError(name)
    return AgentLoop(db_path=str(HISTORIAN), runtime_lm=os.environ["APOLLO_RUNTIME_LM"])


def run() -> dict:
    items = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["items"]
    rows: list[dict] = []
    for name in ("vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"):
        loop = _config_loop(name)
        m = _eval(loop, items)
        m["config"] = name
        rows.append(m)
    payload = {"rows": rows}
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def check() -> int:
    if not RESULTS_PATH.exists():
        print(f"[check] {RESULTS_PATH} missing — run without --check first.", file=sys.stderr)
        return 1
    payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    rows = {r["config"]: r for r in payload["rows"]}
    needed = {"vanilla_opus_4_7", "vanilla_gemma_4_31b", "gepa_gemma"}
    if not needed.issubset(rows):
        print(f"[check] missing rows; have {sorted(rows)}", file=sys.stderr)
        return 1
    opus = rows["vanilla_opus_4_7"]["faithfulness_avg"]
    gepa = rows["gepa_gemma"]["faithfulness_avg"]
    diff_pp = (opus - gepa) * 100.0
    if diff_pp > 2.0:
        print(f"[check] GEPA-Gemma faithfulness {gepa:.3f} > 2pp below Opus {opus:.3f}", file=sys.stderr)
        return 1
    if rows["vanilla_opus_4_7"]["hallucination_count"] != 0:
        print("[check] Opus row had a hallucination", file=sys.stderr)
        return 1
    if rows["gepa_gemma"]["hallucination_count"] != 0:
        print("[check] GEPA-Gemma row had a hallucination", file=sys.stderr)
        return 1
    print(f"[check] OK — Opus {opus:.3f}, GEPA-Gemma {gepa:.3f} (Δ {diff_pp:+.2f}pp)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    payload = run()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
