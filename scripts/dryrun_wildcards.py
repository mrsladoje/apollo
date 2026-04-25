"""Live 'Ask Apollo' 10-question dry-run (PLAN-C §15, FR-W.5).

Loads ``tests/eval/wildcards.json``, runs each question through the in-process
``AgentLoop``, and writes the per-question verdicts to ``docs/dryrun-results.md``.

Pass gate: zero hallucinations across all 10 (refusals on 6/7/8/9 count as
**wins** per ADR-014). Exits 0 iff the gate is met.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from apollo.agent.citations import resolve_citation  # noqa: E402
from apollo.agent.loop import AgentLoop  # noqa: E402

WILDCARDS = REPO_ROOT / "tests" / "eval" / "wildcards.json"
OUT_PATH = REPO_ROOT / "docs" / "dryrun-results.md"
HISTORIAN = REPO_ROOT / "historian.db"


def main() -> int:
    items = json.loads(WILDCARDS.read_text(encoding="utf-8"))["items"]
    os.environ.setdefault("HISTORIAN_DB_PATH", str(HISTORIAN))
    loop = AgentLoop(db_path=str(HISTORIAN))

    passes = 0
    refusals_correct = 0
    fabricated = 0
    rows: list[str] = []

    for item in items:
        resp = loop.answer(item["question"])
        sev_ok = resp.severity in item["expected_severity_in"]
        # Hallucination check: every emitted citation must resolve.
        cit_ok = all(resolve_citation(c) for c in resp.citations)
        if not cit_ok:
            fabricated += 1
        if item["is_unanswerable"] and resp.severity == "REFUSAL":
            refusals_correct += 1
        ok = sev_ok and cit_ok
        passes += int(ok)
        rows.append(
            f"| {item['id']} | {item['question'][:60]}… | {resp.severity} | "
            f"{len(resp.citations)} citations | {'✅' if ok else '❌'} |"
        )

    summary = (
        f"# Apollo wildcard dry-run results\n\n"
        f"Total: {len(items)}\n"
        f"Passes: {passes}/{len(items)}\n"
        f"Refusals correct: {refusals_correct}/4\n"
        f"Fabrications: {fabricated} ({'0 hallucinations' if fabricated == 0 else 'FAIL'})\n\n"
        f"| ID | Question | Severity | Cits | Verdict |\n"
        f"| --- | --- | --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n"
    )
    OUT_PATH.write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if fabricated == 0 and passes == len(items) else 1


if __name__ == "__main__":
    sys.exit(main())
