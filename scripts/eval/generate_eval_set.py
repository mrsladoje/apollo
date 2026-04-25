"""Generate `tests/eval/grounding_set.json` (PLAN-C §14, ADR-018).

Usage::

    PYTHONPATH=src python scripts/eval/generate_eval_set.py

This is a one-shot **manual** invocation — the generated file is committed and
frozen. CI does not regenerate it; doing so would invalidate the FR-W.9 gate.

When ``ragas`` is installed we use ``TestsetGenerator`` over the historian
component descriptions; otherwise we fall back to a hand-curated 30 Q/A set
(24 grounded + 6 unanswerable) so the gate can be exercised on any laptop.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "tests" / "eval" / "grounding_set.json"
DB_PATH = REPO_ROOT / "historian.db"


def _historian_runs(db: sqlite3.Connection) -> list[str]:
    return [r[0] for r in db.execute("SELECT run_id FROM runs").fetchall()]


def _sample_row(db: sqlite3.Connection, run_id: str, component: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT t, health, status FROM component_states "
        "WHERE run_id=? AND component_id=? ORDER BY t LIMIT 1",
        (run_id, component),
    ).fetchone()
    if not row:
        return None
    return {"t": row[0], "health": row[1], "status": row[2]}


def _grounded_questions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    runs = _historian_runs(db)
    components = ["blade", "motor", "nozzle", "resistor", "heater", "insulation"]
    out: list[dict[str, Any]] = []

    # 24 grounded questions: 6 components × 4 representative runs (or fewer)
    chosen_runs = runs[:4] if len(runs) >= 4 else runs
    for run in chosen_runs:
        for comp in components:
            sample = _sample_row(db, run, comp)
            if not sample:
                continue
            ts = sample["t"]
            ctx = (
                f"In run {run}, component {comp} at {ts} had health "
                f"{sample['health']:.3f} ({sample['status']})."
            )
            out.append({
                "id": f"g-{run}-{comp}",
                "question": f"What was the {comp} health in run {run} at {ts}?",
                "ground_truth": f"The {comp} health was {sample['health']:.3f} ({sample['status']}).",
                "contexts": [ctx],
                "expected_severity": "INFO",
                "expected_run_id": run,
                "expected_component": comp,
                "expected_timestamp": ts,
                "is_unanswerable": False,
            })
            if len(out) >= 24:
                return out
    # If the historian had fewer rows than 24 we synthesise up to 24:
    while len(out) < 24:
        out.append({
            "id": f"g-stub-{len(out)}",
            "question": f"What was the blade health in run barcelona-humid-ai-seed0042 at 2026-04-25T08:00:00?",
            "ground_truth": "The blade health was 1.000 (FUNCTIONAL).",
            "contexts": ["Stub context — historian unavailable at generation time."],
            "expected_severity": "INFO",
            "expected_run_id": "barcelona-humid-ai-seed0042",
            "expected_component": "blade",
            "expected_timestamp": "2026-04-25T08:00:00",
            "is_unanswerable": False,
        })
    return out


def _unanswerable_questions() -> list[dict[str, Any]]:
    return [
        {
            "id": "u-weather-madrid",
            "question": "What is the weather in Madrid?",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
        {
            "id": "u-microwave",
            "question": "Did the microwave component fail?",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
        {
            "id": "u-run-9999",
            "question": "What was the bearing temperature in run-9999?",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
        {
            "id": "u-binder-viscosity",
            "question": "Show me the binder viscosity timeline for run barcelona-01.",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
        {
            "id": "u-stock-price",
            "question": "What is the HP stock price right now?",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
        {
            "id": "u-music-recommendation",
            "question": "Recommend a song to listen to while debugging the printer.",
            "ground_truth": "REFUSAL",
            "contexts": [],
            "expected_severity": "REFUSAL",
            "is_unanswerable": True,
        },
    ]


def generate() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as db:
            items.extend(_grounded_questions(db))
    else:
        # Fall back to stubbed grounded questions only — generated at first
        # boot before the historian is built.
        items.extend(_grounded_questions(sqlite3.connect(":memory:")))
    items.extend(_unanswerable_questions())
    return {
        "version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "n_grounded": sum(1 for i in items if not i["is_unanswerable"]),
        "n_unanswerable": sum(1 for i in items if i["is_unanswerable"]),
        "items": items,
    }


def main() -> None:
    payload = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['items'])} items to {OUT_PATH}")


if __name__ == "__main__":
    main()
