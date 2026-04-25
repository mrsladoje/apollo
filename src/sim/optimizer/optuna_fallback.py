"""Optuna fallback — PLAN-B §9.6 / ADR-011 contingency.

Same 7-dim encoding and same fitness function as ``sim.optimizer.ga`` so
the AIPolicy threshold semantics are preserved across the swap. Built but
dormant: invoked only if the GA fitness landscape comes out flat or jagged
in the dry run.

Output contract: writes the same ``data/ga_fitness.csv`` and
``config/policies.yaml`` files so Plan C's Recharts panel and the runtime
policy loader see the same shape regardless of which optimizer ran.
"""

from __future__ import annotations

import csv
import os
import statistics
from typing import List, Tuple

from .ga import (
    GA_FITNESS_CSV,
    GENE_ORDER,
    POLICIES_YAML,
    SEED_INDIVIDUAL,
    _evaluate,
    _write_policies_yaml,
)


def _suggest_individual(trial) -> List[float]:
    return [
        trial.suggest_float(f"gene_{i}", 0.0, 1.0) for i in range(7)
    ]


def optimize_with_optuna(
    n_trials: int = 200,
    seed: int = 42,
    csv_path: str = GA_FITNESS_CSV,
    yaml_path: str = POLICIES_YAML,
) -> Tuple[List[float], float]:
    """Run an Optuna TPE search over the same 7-dim space.

    Determinism: same ``seed`` + same fitness function ⇒ same final params
    (Optuna's TPE sampler is seeded). Returns ``(best_individual, best_value)``.
    """
    import optuna  # type: ignore

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    # Seed the study with §9.3's hand-tuned individual so the curve doesn't
    # start from random — matches the GA's seeding strategy.
    seed_params = {f"gene_{i}": SEED_INDIVIDUAL[i] for i in range(7)}
    study.enqueue_trial(seed_params)

    history: List[float] = []

    def objective(trial):
        ind = _suggest_individual(trial)
        score = _evaluate(ind)[0]
        history.append(score)
        return score

    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    # Mirror the GA CSV schema so Plan C's panel can read either run.
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "generation",
                "best_fitness",
                "mean_fitness",
                "std_fitness",
            ],
        )
        writer.writeheader()
        running_best = float("-inf")
        for i, val in enumerate(history):
            running_best = max(running_best, val)
            window = history[: i + 1]
            writer.writerow(
                {
                    "generation": i,
                    "best_fitness": running_best,
                    "mean_fitness": statistics.mean(window),
                    "std_fitness": (
                        statistics.stdev(window) if len(window) > 1 else 0.0
                    ),
                }
            )

    best_params = study.best_params
    best_individual = [best_params[f"gene_{i}"] for i in range(7)]
    _write_policies_yaml(best_individual, study.best_value, n_trials, path=yaml_path)
    return best_individual, float(study.best_value)


__all__ = ["optimize_with_optuna"]
