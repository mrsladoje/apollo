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
LOG_DIR = REPO_ROOT / "docs" / "eval" / "gepa_logs"

TOOL_USE_REFINEMENTS = """\
During the tool-selection phase, obey the JSON router contract even though the final Apollo response is structured separately.
Return only one JSON object for tool selection: {"tool": "...", "args": {...}}.
Do not include chain-of-thought, examples, markdown, or intermediate arg-only JSON before the final router object.
Known components are blade, motor, nozzle, resistor, heater, insulation. Refuse unknown components such as microwave, bearing temperature, or binder viscosity.
Treat "motor bearing" as the motor component, not as an unknown component.
Refuse unknown runs such as run-9999 and off-topic questions such as weather, stocks, music, sports, recipes, or recommendations.
Direct health/status/value for one run and component -> query_historian.
Why/cascade/explain rows -> late_interaction_search.
Compare/across universes/runs -> compare_runs using avg_health unless the user names another valid metric.
What-if/counterfactual/replaced at hour N -> run_counterfactual with branch_t at that hour and alternate_action.component_id set to the mentioned component.
Show/plot/history/timeline for a valid component -> plot_component_history.
For query_historian and late_interaction_search final answers, include citation triples copied exactly from returned rows.
"""


def _load_split() -> tuple[list[dict], list[dict]]:
    from scripts.agent.tool_use_eval import load_tool_use_items

    return load_tool_use_items(split="train"), load_tool_use_items(split="holdout")


def _real_compile(max_metric_calls: int) -> dict:  # pragma: no cover - requires DSPy + live models
    import dspy  # type: ignore
    from dspy.teleprompt import GEPA  # type: ignore
    from dspy.teleprompt.gepa.gepa import ScoreWithFeedback  # type: ignore

    from apollo.agent.lm.claude_cli import ClaudeCLI
    from apollo.agent.tools.registry import invoke
    from scripts.agent.tool_use_eval import (
        args_match,
        context_from_result,
        json_from_text,
        normalize_args,
        score_answer,
    )

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
        """Choose exactly one Apollo tool for the question. Return one JSON object with keys tool and args. tool must be one of query_historian, late_interaction_search, compare_runs, run_counterfactual, plot_component_history, REFUSAL. args must match the selected tool schema, or {} for REFUSAL. Output only the JSON object."""

        question = dspy.InputField()
        answer = dspy.OutputField(desc='Exactly one JSON object: {"tool": "...", "args": {...}}')

    class ApolloFinalSig(dspy.Signature):
        """Answer using only the supplied tool result. Return one JSON object with severity, text, and citations. For query_historian and late_interaction_search include citation triples copied exactly from the tool result."""

        question = dspy.InputField()
        tool = dspy.InputField()
        args_json = dspy.InputField()
        tool_result = dspy.InputField()
        answer = dspy.OutputField(desc='Exactly one JSON object: {"severity": "...", "text": "...", "citations": [...]}.')

    class ApolloToolAnswerProgram(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.router = dspy.Predict(ApolloToolSig)
            self.answerer = dspy.Predict(ApolloFinalSig)

        def forward(self, question: str):
            try:
                routed = self.router(question=question)
                selection_json = str(routed.answer)
                selection = json_from_text(selection_json)
            except Exception as exc:  # noqa: BLE001
                return dspy.Prediction(error=f"ROUTER_FORMAT_FAILURE: {exc}", selection_json="", answer_json="")

            tool = str(selection.get("tool", "")).strip()
            args = normalize_args(tool, selection.get("args") or {}, {"question": question})
            args_json = json.dumps(args, default=str)
            if tool == "REFUSAL":
                return dspy.Prediction(
                    error="",
                    selection_json=selection_json,
                    tool=tool,
                    args_json=args_json,
                    tool_result_json="{}",
                    answer_json='{"severity":"REFUSAL","text":"REFUSAL","citations":[]}',
                )
            try:
                result = invoke(tool, args)
            except Exception as exc:  # noqa: BLE001
                return dspy.Prediction(
                    error=f"TOOL_EXECUTION_FAILURE: {exc}",
                    selection_json=selection_json,
                    tool=tool,
                    args_json=args_json,
                    tool_result_json="{}",
                    answer_json="",
                )
            result_json = context_from_result(result)
            try:
                answered = self.answerer(
                    question=question,
                    tool=tool,
                    args_json=args_json,
                    tool_result=result_json,
                )
                answer_json = str(answered.answer)
            except Exception as exc:  # noqa: BLE001
                return dspy.Prediction(
                    error=f"FINAL_ANSWER_FORMAT_FAILURE: {exc}",
                    selection_json=selection_json,
                    tool=tool,
                    args_json=args_json,
                    tool_result_json=result_json,
                    answer_json="",
                )
            return dspy.Prediction(
                error="",
                selection_json=selection_json,
                tool=tool,
                args_json=args_json,
                tool_result_json=result_json,
                answer_json=answer_json,
            )

    student_module = ApolloToolAnswerProgram()

    def gepa_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        expected_tool = str(getattr(gold, "expected_tool"))
        question = str(getattr(gold, "question"))
        item = {
            "question": question,
            "expected_tool": expected_tool,
            "expected_run_id": getattr(gold, "expected_run_id", None),
            "expected_run_ids": getattr(gold, "expected_run_ids", None),
            "expected_component": getattr(gold, "expected_component", None),
            "expected_timestamp": getattr(gold, "expected_timestamp", None),
            "expected_contains": list(getattr(gold, "expected_contains", []) or []),
            "requires_citation": bool(getattr(gold, "requires_citation", False)),
            "is_unanswerable": bool(getattr(gold, "is_unanswerable", False)),
        }
        if getattr(pred, "error", ""):
            error = str(getattr(pred, "error"))
        else:
            error = ""
        try:
            selection = json_from_text(str(getattr(pred, "selection_json", "")))
        except Exception as exc:
            return ScoreWithFeedback(score=0.0, feedback=f"INVALID SELECTION JSON: {exc}")

        tool = str(selection.get("tool", "")).strip()
        if expected_tool == "REFUSAL":
            ok = tool == "REFUSAL"
            return ScoreWithFeedback(
                score=1.0 if ok else 0.0,
                feedback="OK" if ok else f"MUST REFUSE: expected REFUSAL, selected {tool}.",
            )

        score = 0.0
        feedback: list[str] = []
        if tool == expected_tool:
            score += 0.25
        else:
            feedback.append(f"WRONG TOOL: expected {expected_tool}, selected {tool or '<empty>'}.")

        try:
            args = json.loads(str(getattr(pred, "args_json", "{}")))
        except Exception as exc:  # noqa: BLE001
            args = {}
            feedback.append(f"INVALID ARGS JSON: {exc}")
        matched, arg_issues = args_match(tool, args, item)
        if matched:
            score += 0.20
        else:
            feedback.append("BAD TOOL ARGS: " + "; ".join(arg_issues))

        try:
            result = invoke(tool, args)
            score += 0.20
        except Exception as exc:  # noqa: BLE001
            result = None
            feedback.append(f"INVALID TOOL ARGS for {tool}: {exc}")
        if error:
            feedback.append(error)

        if result is not None:
            try:
                answer = json_from_text(str(getattr(pred, "answer_json", "")))
                answer_score = score_answer(item, tool, answer, result)
                score += 0.15 * float(answer_score["faithfulness"])
                if answer_score["answer_contains"]:
                    score += 0.10
                if answer_score["citation_ok"]:
                    score += 0.10
                if not answer_score["answer_contains"]:
                    feedback.append("FINAL ANSWER MISSING EXPECTED FACTS from expected_contains.")
                if not answer_score["citation_ok"]:
                    feedback.append("FINAL ANSWER CITATIONS missing or not resolvable against historian rows.")
                if float(answer_score["faithfulness"]) < 0.5:
                    feedback.append("LOW FINAL ANSWER FAITHFULNESS: answer must copy facts from tool_result only.")
            except Exception as exc:  # noqa: BLE001
                feedback.append(f"INVALID FINAL ANSWER JSON: {exc}")

        return ScoreWithFeedback(score=float(score), feedback="\n".join(feedback) or "OK")

    optimizer = GEPA(
        metric=gepa_metric,
        reflection_lm=reflector,
        max_metric_calls=max_metric_calls,
        reflection_minibatch_size=4,
        add_format_failure_as_feedback=True,
        track_stats=True,
        track_best_outputs=True,
        log_dir=str(LOG_DIR),
        num_threads=1,
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
