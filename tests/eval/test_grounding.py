"""DeepEval-style grounding gate (PLAN-C §14, ADR-018, FR-W.9).

The pure-pytest harness runs Apollo end-to-end through the in-process
``AgentLoop`` for each Q/A and asserts:
  * faithfulness ≥ 0.95 over the 24 grounded items
  * hallucination = 0 over all 30 (i.e. for every question, no fabricated
    citations are emitted)
  * 6 unanswerable questions return ``severity = REFUSAL``

When ``deepeval`` is installed the same harness can be invoked with
``deepeval test run tests/eval/`` per §19.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from apollo.agent.citations import resolve_citation
from apollo.agent.contracts import ApolloResponse
from apollo.agent.loop import AgentLoop
from apollo.agent.metric import _faithfulness


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = REPO_ROOT / "tests" / "eval" / "grounding_set.json"
HISTORIAN_DB = REPO_ROOT / "historian.db"


def _load_eval() -> dict:
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def loop() -> AgentLoop:
    os.environ.setdefault("HISTORIAN_DB_PATH", str(HISTORIAN_DB))
    return AgentLoop(db_path=str(HISTORIAN_DB))


@pytest.fixture(scope="module")
def dataset() -> list[dict]:
    if not EVAL_PATH.exists():  # pragma: no cover — generate_eval_set first
        pytest.skip("grounding_set.json not generated")
    return _load_eval()["items"]


def _answer(loop: AgentLoop, item: dict) -> ApolloResponse:
    return loop.answer(item["question"], item.get("expected_run_id"))


def test_eval_set_size_and_split() -> None:
    data = _load_eval()
    assert data["n_grounded"] == 24
    assert data["n_unanswerable"] == 6
    assert len(data["items"]) == 30


def test_unanswerable_questions_refuse(loop: AgentLoop, dataset: list[dict]) -> None:
    """All 6 unanswerable questions must yield REFUSAL with no citations."""
    refusals = [item for item in dataset if item["is_unanswerable"]]
    assert len(refusals) == 6
    for item in refusals:
        resp = _answer(loop, item)
        assert resp.severity == "REFUSAL", item["id"]
        assert resp.citations == [], item["id"]


def test_no_fabricated_citations(loop: AgentLoop, dataset: list[dict]) -> None:
    """Hallucination = 0 — every emitted citation must resolve."""
    for item in dataset:
        resp = _answer(loop, item)
        for c in resp.citations:
            assert resolve_citation(c), f"fabricated citation in {item['id']}: {c}"


def test_faithfulness_over_grounded(loop: AgentLoop, dataset: list[dict]) -> None:
    """Faithfulness ≥ 0.95 over the 24 grounded items (FR-W.9 / NFR-6)."""
    scores: list[float] = []
    for item in dataset:
        if item["is_unanswerable"]:
            continue
        resp = _answer(loop, item)
        score = _faithfulness(resp.text, item.get("contexts", []))
        scores.append(score)
    avg = sum(scores) / len(scores) if scores else 0.0
    assert avg >= 0.95, f"faithfulness {avg:.3f} < 0.95"
