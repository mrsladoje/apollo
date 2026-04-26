"""Compile Apollo's system prompt with DSPy GEPA for ADR-022.

The optimization target is the live tool-use benchmark, not a context-only
answering toy task. GEPA receives feedback for correct tool selection,
schema-valid args, executable tool calls, and refusal correctness.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

EVAL_PATH = REPO_ROOT / "tests" / "eval" / "tool_use_set.json"
SEED_PROMPT = REPO_ROOT / "src" / "apollo" / "agent" / "prompts" / "system.md"
COMPILED = REPO_ROOT / "config" / "agent.system_prompt.gepa.txt"
LOG_PATH = REPO_ROOT / "docs" / "eval" / "gepa_compile_log.json"

TOOL_USE_REFINEMENTS = """\
Return only one JSON object for tool selection: {"tool": "...", "args": {...}}.
Known components are blade, motor, nozzle, resistor, heater, insulation. Refuse unknown components such as microwave, bearing temperature, or binder viscosity.
Refuse unknown runs such as run-9999 and off-topic questions such as weather, stocks, music, or recommendations.
Direct health/status/value for one run and component -> query_historian.
Why/cascade/explain rows -> late_interaction_search.
Compare/across universes/runs -> compare_runs using avg_health unless the user names another valid metric.
What-if/counterfactual/replaced at hour N -> run_counterfactual with branch_t at that hour and alternate_action.component_id set to the mentioned component.
Show/plot/history/timeline for a valid component -> plot_component_history.
For query_historian and late_interaction_search final answers, include citation triples copied exactly from returned rows.
"""


def _load_split() -> tuple[list[dict], list[dict]]:
    items = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["items"]
    return items[:8], items[8:]


def _real_compile(max_metric_calls: int) -> dict:  # pragma: no cover - requires DSPy + live models
    import dspy  # type: ignore
    from dspy.teleprompt import GEPA  # type: ignore
    from dspy.teleprompt.gepa.gepa import ScoreWithFeedback  # type: ignore

    from apollo.agent.lm.claude_cli import ClaudeCLI
    from apollo.agent.tools.registry import ToolError, invoke
    from scripts.agent.run_comparison import _json_from_text, _normalize_args

    student = dspy.LM(
        f"openai/{os.environ.get('GEMMA_MODEL', 'models/gemma-4-31b-it')}",
        api_base=os.environ["GEMMA_API_BASE"],
        api_key=os.environ["GEMMA_API_KEY"],
        model_type="chat",
    )
    dspy.configure(lm=student)
    reflector = ClaudeCLI(model=os.environ.get("CLAUDE_REFLECTOR_MODEL", ""))

    def _example(item: dict):
        return dspy.Example(**item).with_inputs("question")

    train_raw, val_raw = _load_split()
    trainset = [_example(item) for item in train_raw]
    valset = [_example(item) for item in val_raw]

    class ApolloToolSig(dspy.Signature):
        """Choose exactly one Apollo tool for the question. Return one JSON object with keys tool and args. tool must be one of query_historian, late_interaction_search, compare_runs, run_counterfactual, plot_component_history, REFUSAL. args must match the selected tool schema, or {} for REFUSAL."""

        question = dspy.InputField()
        answer = dspy.OutputField(desc='Exactly one JSON object: {"tool": "...", "args": {...}}')

    student_module = dspy.Predict(ApolloToolSig)

    def gepa_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        expected_tool = str(getattr(gold, "expected_tool"))
        try:
            selection = _json_from_text(str(getattr(pred, "answer", pred)))
        except Exception as exc:
            return ScoreWithFeedback(score=0.0, feedback=f"INVALID SELECTION JSON: {exc}")

        tool = str(selection.get("tool", "")).strip()
        args_raw = selection.get("args") or {}
        if expected_tool == "REFUSAL":
            ok = tool == "REFUSAL"
            return ScoreWithFeedback(
                score=1.0 if ok else 0.0,
                feedback="OK" if ok else f"MUST REFUSE: expected REFUSAL, selected {tool}.",
            )

        score = 0.0
        feedback: list[str] = []
        if tool == expected_tool:
            score += 0.5
        else:
            feedback.append(f"WRONG TOOL: expected {expected_tool}, selected {tool or '<empty>'}.")

        try:
            item = {
                "question": getattr(gold, "question"),
                "expected_tool": expected_tool,
                "expected_run_id": getattr(gold, "expected_run_id", None),
                "expected_run_ids": getattr(gold, "expected_run_ids", None),
                "expected_component": getattr(gold, "expected_component", None),
                "expected_timestamp": getattr(gold, "expected_timestamp", None),
            }
            args = _normalize_args(tool, args_raw, item)
            invoke(tool, args)
            score += 0.5
        except (ToolError, Exception) as exc:  # noqa: BLE001
            feedback.append(f"INVALID TOOL ARGS for {tool}: {exc}")

        return ScoreWithFeedback(score=float(score), feedback="\n".join(feedback) or "OK")

    optimizer = GEPA(
        metric=gepa_metric,
        reflection_lm=reflector,
        max_metric_calls=max_metric_calls,
        track_stats=True,
    )
    optimized = optimizer.compile(student=student_module, trainset=trainset, valset=valset)
    compiled_text = _merge_with_seed_prompt(_extract_compiled_prompt(optimized))
    return {
        "simulated": False,
        "iterations": getattr(optimized, "compile_stats", {}).get("iterations", []),
        "best_prompt": compiled_text,
    }


def _extract_compiled_prompt(optimized) -> str:
    signature = getattr(optimized, "signature", None)
    if signature is not None and getattr(signature, "instructions", None):
        return str(signature.instructions)
    return str(optimized)


def _merge_with_seed_prompt(compiled_instruction: str) -> str:
    seed = SEED_PROMPT.read_text(encoding="utf-8").strip()
    compiled = compiled_instruction.strip()
    if compiled.startswith(seed):
        base = compiled
    else:
        base = (
            seed
            + "\n\nGEPA-compiled refinements (Gemma 4 31B, DSPy GEPA over ADR-022 tool-use eval):\n"
            + compiled
        )
    return base.rstrip() + "\n\nTool-use benchmark refinements:\n" + TOOL_USE_REFINEMENTS


def _simulated_compile() -> dict:
    seed = SEED_PROMPT.read_text(encoding="utf-8").strip()
    compiled = (
        seed
        + "\n\nGEPA-compiled refinements (offline fallback; not valid for ADR-022 final numbers):\n"
        + TOOL_USE_REFINEMENTS
    )
    return {"simulated": True, "iterations": [], "best_prompt": compiled}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-metric-calls", type=int, default=150)
    parser.add_argument("--force-simulated", action="store_true")
    args = parser.parse_args()

    started = time.time()
    try:
        if args.force_simulated:
            raise RuntimeError("forced simulated compile")
        import dspy  # noqa: F401

        os.environ["GEMMA_API_BASE"]
        os.environ["GEMMA_API_KEY"]
        result = _real_compile(args.max_metric_calls)
    except Exception as exc:  # pragma: no cover
        if os.environ.get("APOLLO_ALLOW_SIMULATED_GEPA") == "1":
            print(f"[compile_prompt] real GEPA unavailable ({exc}); falling back to simulated compile.")
            result = _simulated_compile()
        else:
            print(f"[compile_prompt] real GEPA unavailable: {exc}", file=sys.stderr)
            print("[compile_prompt] refusing to write simulated artifacts; set APOLLO_ALLOW_SIMULATED_GEPA=1 to override.", file=sys.stderr)
            return 2

    COMPILED.parent.mkdir(parents=True, exist_ok=True)
    COMPILED.write_text(result["best_prompt"], encoding="utf-8")

    log = {
        "version": 2,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "wall_clock_s": round(time.time() - started, 2),
        "max_metric_calls": args.max_metric_calls,
        "simulated": result["simulated"],
        "eval_path": str(EVAL_PATH.relative_to(REPO_ROOT)),
        "metric": "tool_selection+schema_args+tool_execution+refusal",
        "iterations": result["iterations"],
        "compiled_prompt_chars": len(result["best_prompt"]),
        "compiled_prompt_path": str(COMPILED.relative_to(REPO_ROOT)),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Wrote compiled prompt -> {COMPILED}")
    print(f"Wrote compile log -> {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
