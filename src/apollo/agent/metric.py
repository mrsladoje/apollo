"""GEPA metric with feedback (PLAN-C §14a.4).

Per Decagon production tuning notes, the textual ``feedback`` string is the
primary optimization channel — the scalar score alone underperforms.

The metric returns a ``dspy.Prediction`` when DSPy is available; otherwise a
plain dataclass with ``score`` and ``feedback`` fields. Either way the same
shape works for the GEPA reflector.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from .citations import resolve_citation
from .contracts import ApolloResponse, CANONICAL_COMPONENTS, Citation
from .tools import REGISTRY


@dataclass
class MetricResult:
    score: float
    feedback: str

    # ``dspy.Prediction`` is dict-like; tests access either form.
    def __iter__(self):  # pragma: no cover — DSPy compat shim
        yield "score", self.score
        yield "feedback", self.feedback


def _to_response(obj: Any) -> ApolloResponse:
    if isinstance(obj, ApolloResponse):
        return obj
    if hasattr(obj, "model_dump"):
        return ApolloResponse(**obj.model_dump())
    if isinstance(obj, dict):
        return ApolloResponse(**obj)
    raise TypeError(f"Cannot coerce {type(obj)!r} into ApolloResponse")


def _validate_tool_args(name: str, args: dict[str, Any]) -> tuple[bool, str]:
    if name not in REGISTRY:
        return False, f"unknown tool {name!r}"
    model = REGISTRY[name]["args_model"]
    try:
        model(**args)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, ""


def metric_with_feedback(
    example: Any,
    pred: Any,
    trace: Any = None,
    db: Optional[sqlite3.Connection] = None,
):
    """The GEPA optimization signal.

    ``example`` should expose ``contexts`` (list[str]) and an optional
    ``is_unanswerable`` flag. ``pred`` is anything coercible into
    ``ApolloResponse``.
    """
    response = _to_response(pred)
    feedback: list[str] = []
    score = 0.0

    # ----- 1. Schema validity on every tool call -------------------------
    bad_tools = []
    for tc in response.tool_calls:
        ok, err = _validate_tool_args(tc.tool, tc.args)
        if not ok:
            bad_tools.append((tc.tool, err))
    if not bad_tools:
        score += 0.2
    else:
        feedback.append(
            "INVALID TOOL ARGS: " + "; ".join(f"{t}: {e}" for t, e in bad_tools)
        )

    # ----- 2. Citations resolve against the historian --------------------
    is_unanswerable = bool(getattr(example, "is_unanswerable", False)) or (
        isinstance(example, dict) and example.get("is_unanswerable")
    )
    if response.severity == "REFUSAL":
        if is_unanswerable:
            score += 0.5  # 0.3 + 0.2 — credit for both invariants in one move
        else:
            feedback.append(
                "OVER-REFUSED: example is answerable but you returned REFUSAL."
            )
    else:
        unresolved: list[Citation] = []
        for c in response.citations:
            if c.component.value not in CANONICAL_COMPONENTS:
                feedback.append(
                    f"INVALID COMPONENT: {c.component!r} is not in the 6-component enum."
                )
                continue
            if not resolve_citation(c, db):
                unresolved.append(c)
        if unresolved:
            feedback.append(
                "FABRICATED CITATIONS: "
                + "; ".join(f"{c.run_id}/{c.component.value}@{c.timestamp.isoformat()}" for c in unresolved)
                + " — these triples don't exist in the historian."
            )
        else:
            score += 0.3
            if is_unanswerable:
                feedback.append("MUST REFUSE: no telemetry supports this question; do not guess.")
            else:
                score += 0.2

    # ----- 3. Faithfulness on the prose (DeepEval if available) ----------
    contexts = getattr(example, "contexts", None) or (
        example.get("contexts") if isinstance(example, dict) else None
    ) or []
    faith = _faithfulness(response.text, list(contexts))
    score += 0.3 * faith
    if faith < 0.95 and response.severity != "REFUSAL":
        feedback.append(
            f"LOW FAITHFULNESS ({faith:.2f}): one or more claims in the response "
            "are not supported by the retrieved context."
        )

    feedback_str = "\n".join(feedback) if feedback else "OK"
    result = MetricResult(score=score, feedback=feedback_str)

    # When DSPy is present, prefer to return a ``dspy.Prediction`` so GEPA can
    # introspect it natively.
    try:  # pragma: no cover — exercised only when dspy is installed
        import dspy  # type: ignore

        return dspy.Prediction(score=score, feedback=feedback_str)
    except Exception:
        return result


def _faithfulness(text: str, contexts: list[str]) -> float:
    """DeepEval ``FaithfulnessMetric`` if available; degrade gracefully.

    Fallback heuristic — proxies the production metric:

    * If every ``len > 4`` word in the response also appears in the joined
      contexts (i.e. the response is a strict subset of the context
      vocabulary), score = 1.0 — nothing was made up.
    * Otherwise penalize linearly by the fraction of unsupported words.
    * Empty contexts → 0.5 (neither pass nor fail; the caller should treat
      this as "needs human review").
    """
    try:  # pragma: no cover — DeepEval optional in tests
        from deepeval.metrics import FaithfulnessMetric  # type: ignore
        from deepeval.test_case import LLMTestCase  # type: ignore

        m = FaithfulnessMetric(threshold=0.95)
        case = LLMTestCase(input="", actual_output=text, retrieval_context=contexts)
        m.measure(case)
        return float(m.score or 0.0)
    except Exception:
        if not text:
            return 0.0
        if not contexts:
            return 0.5
        joined = " ".join(contexts).lower()
        # Strip punctuation; only consider content words.
        STOPWORDS = {
            "the", "and", "for", "with", "from", "that", "this", "have", "had",
            "was", "were", "are", "across", "into", "over", "after", "before",
            "queried", "rows", "historian", "component", "state", "states",
        }
        words = [
            w.strip(".,;:!?\"()[]{}").lower()
            for w in text.split()
            if len(w.strip(".,;:!?\"()[]{}")) > 3
        ]
        words = [w for w in words if w and w not in STOPWORDS]
        if not words:
            return 1.0
        hits = sum(1 for w in words if w in joined)
        ratio = hits / len(words)
        # Boost when the response quotes a long token verbatim (run_id, ISO ts).
        for token in text.split():
            t = token.strip(".,;:!?\"()[]{}")
            if len(t) >= 12 and t.lower() in joined:
                ratio = min(1.0, ratio + 0.15)
        return min(1.0, ratio)


__all__ = ["MetricResult", "metric_with_feedback"]
