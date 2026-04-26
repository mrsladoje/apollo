"""Pre-run the canonical 3x3 scenario grid into ``historian.db``.

This is the script named by PLAN.md's master Definition of Done. It is a thin,
deterministic wrapper around Plan B's simulation loop: three scenarios, three
policies, stable seed, stable run IDs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sim.config import SimulationConfig
from sim.loop import run_simulation

SCENARIOS = ("barcelona-humid", "phoenix-dry", "stressed")
POLICIES = ("none", "fixed", "ai")


def prerun_scenarios(
    historian_path: str = "historian.db",
    *,
    seed: int = 42,
    horizon_minutes: int = 600,
) -> list[str]:
    Path(historian_path).parent.mkdir(parents=True, exist_ok=True)
    run_ids: list[str] = []
    for scenario in SCENARIOS:
        for policy in POLICIES:
            cfg = SimulationConfig.from_run_params(
                scenario_name=scenario,
                policy=policy,
                seed=seed,
                horizon_minutes=horizon_minutes,
                historian_path=historian_path,
            )
            run_id = run_simulation(cfg)
            run_ids.append(run_id)
            print(f"[prerun] {run_id}")
    return run_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historian", default="historian.db")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--horizon-minutes", type=int, default=600)
    args = parser.parse_args()

    run_ids = prerun_scenarios(
        args.historian,
        seed=args.seed,
        horizon_minutes=args.horizon_minutes,
    )
    print(f"[prerun] wrote {len(run_ids)} runs to {args.historian}")


if __name__ == "__main__":
    main()
