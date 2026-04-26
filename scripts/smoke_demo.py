"""End-to-end smoke test for the canonical Apollo demo path.

This intentionally avoids a live LLM call. It verifies the deterministic demo
substrate: historian rows exist, Plan C tools reach Plan B contracts, citations
can resolve, and What-If returns a real counterfactual projection.
"""

from __future__ import annotations

import argparse
import os
from datetime import timedelta
from pathlib import Path

from apollo.agent.tools.registry import invoke
from engine.contracts import ComponentId
from sim.drivers.composite import SIM_START_TIME
from sim.historian.reader import query_historian

CANONICAL_RUN_ID = "barcelona-humid-none-seed0042"


def smoke_demo(historian_path: str = "historian.db") -> None:
    path = Path(historian_path)
    if not path.exists():
        raise SystemExit(
            f"{historian_path} does not exist. Run `python scripts/prerun_scenarios.py` "
            "or `make build-grid` first."
        )

    os.environ["HISTORIAN_BACKEND"] = "real"
    os.environ["HISTORIAN_PATH"] = historian_path
    os.environ.setdefault("RETRIEVAL_BACKEND", "dense")
    os.environ.setdefault("APOLLO_TOOLS_BACKEND", "auto")

    start = SIM_START_TIME + timedelta(minutes=300)
    end = SIM_START_TIME + timedelta(minutes=360)

    rows = invoke(
        "query_historian",
        {
            "run_id": CANONICAL_RUN_ID,
            "component": ComponentId.NOZZLE.value,
            "time_range": (start, end),
        },
    )
    if not rows:
        raise AssertionError("canonical query returned no historian rows")

    citation_row = query_historian(
        CANONICAL_RUN_ID,
        ComponentId.NOZZLE,
        (start, end),
        db_path=historian_path,
    )[0]
    resolved = query_historian(
        citation_row.run_id,
        citation_row.component_id,
        (citation_row.t, citation_row.t),
        db_path=historian_path,
    )
    if not resolved:
        raise AssertionError("canonical citation did not resolve")

    comparison = invoke(
        "compare_runs",
        {
            "run_ids": [
                "barcelona-humid-none-seed0042",
                "barcelona-humid-fixed-seed0042",
                "barcelona-humid-ai-seed0042",
            ],
            "metric": "avg_health",
        },
    )
    if len(comparison) != 3:
        raise AssertionError("compare_runs did not return all three Barcelona policies")

    retrieved = invoke(
        "late_interaction_search",
        {
            "query": "nozzle thermal cascade",
            "run_id": CANONICAL_RUN_ID,
            "top_k": 5,
        },
    )
    if not retrieved:
        raise AssertionError("retrieval returned no rows")

    counterfactual = invoke(
        "run_counterfactual",
        {
            "run_id": CANONICAL_RUN_ID,
            "branch_t": SIM_START_TIME + timedelta(minutes=30),
            "alternate_action": {
                "action": "MAINTENANCE",
                "component_id": ComponentId.NOZZLE.value,
            },
        },
    )
    diff = counterfactual.get("diff", {})
    if {"uptime_delta", "failures_avoided", "cost_delta"} - set(diff):
        raise AssertionError(f"counterfactual diff missing keys: {diff}")

    print("[smoke_demo] OK")
    print(f"[smoke_demo] historian rows: {len(rows)}")
    print(f"[smoke_demo] retrieval rows: {len(retrieved)}")
    print(f"[smoke_demo] counterfactual diff: {diff}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historian", default="historian.db")
    args = parser.parse_args()
    smoke_demo(args.historian)


if __name__ == "__main__":
    main()
