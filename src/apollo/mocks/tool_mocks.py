"""Mock implementations of the five Plan-C tools using in-memory data
(PLAN-C §4.1). These mirror the sim.contracts signatures.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from engine.contracts import ComponentId

COMPONENTS: list[str] = [c.value for c in ComponentId]

# Canned historian rows keyed by (run_id, component)
HISTORIAN_DATA: dict[tuple[str, str], list[dict]] = {}

_START = datetime(2026, 4, 25, 8, 0, 0, tzinfo=timezone.utc)


def _seed_run(run_id: str, seed: int = 42) -> None:
    rng = random.Random(seed)
    for comp in COMPONENTS:
        rows = []
        health = 1.0
        for minute in range(0, 121, 5):
            health -= rng.uniform(0.01, 0.06)
            health = max(0.0, health)
            rows.append({
                "run_id": run_id,
                "t": float(minute),
                "component_id": comp,
                "health": round(health, 3),
                "status": _status(health),
                "metrics_json": json.dumps({"temp_C": rng.uniform(60, 95)}),
            })
        HISTORIAN_DATA[(run_id, comp)] = rows


def _status(h: float) -> str:
    if h >= 0.7:
        return "FUNCTIONAL"
    if h >= 0.4:
        return "DEGRADED"
    if h >= 0.1:
        return "CRITICAL"
    return "FAILED"


# Pre-seed the three canonical runs
_seed_run("barcelona-01", seed=10)
_seed_run("phoenix-02", seed=20)
_seed_run("dark-twin-00", seed=5)


def query_historian(run_id: str, component: str, time_range: list[float]) -> list[dict]:
    rows = HISTORIAN_DATA.get((run_id, component), [])
    lo, hi = time_range[0], time_range[1]
    return [r for r in rows if lo <= r["t"] <= hi]


def late_interaction_search(query: str, run_id: Optional[str] = None) -> list[dict]:
    results = []
    source = HISTORIAN_DATA
    for (rid, comp), rows in source.items():
        if run_id and rid != run_id:
            continue
        if any(word in comp for word in query.lower().split()):
            if rows:
                results.append({**rows[-1], "score": 0.85})
    return results[:5]


def compare_runs(run_ids: list[str], metric: str) -> dict:
    comparison: dict[str, list] = {}
    for run_id in run_ids:
        vals = []
        for comp in COMPONENTS:
            rows = HISTORIAN_DATA.get((run_id, comp), [])
            if rows:
                vals.append(rows[-1]["health"])
        comparison[run_id] = vals
    return {"run_ids": run_ids, "metric": metric, "data": comparison}


def run_counterfactual(run_id: str, branch_t: float, alt_action: str) -> dict:
    rng = random.Random(hash(run_id + alt_action))
    original = []
    alt = []
    health_orig = 0.8
    health_alt = 0.95
    for t in range(int(branch_t), int(branch_t) + 61, 5):
        health_orig -= rng.uniform(0.02, 0.07)
        health_alt -= rng.uniform(0.01, 0.04)
        original.append({"t": float(t), "health": round(max(0, health_orig), 3)})
        alt.append({"t": float(t), "health": round(max(0, health_alt), 3)})
    delta = sum(a["health"] for a in alt) - sum(o["health"] for o in original)
    return {
        "run_id": run_id,
        "branch_t": branch_t,
        "alt_action": alt_action,
        "original_health": original,
        "alt_health": alt,
        "uptime_delta_h": round(delta * 0.5, 2),
    }
