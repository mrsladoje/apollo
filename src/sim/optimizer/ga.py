"""DEAP GA — PLAN-B §9 Workstream B5.

Tunes the AIPolicy's 7-dim genome (6 per-component thresholds + 1 global
lookahead coefficient) on the Stressed scenario, where the fitness landscape
is most informative (ADR-011).

Notes vs. earlier revision:
- ``deap`` is imported lazily so importing this module on a machine without
  the dep does not crash (R-7 / offline CI).
- The fitness function now actually wires the genome into ``SimulationConfig``
  (previous revision dropped the genome into ``config_json``, which the loop
  ignored — every individual evaluated to the same default policy and the
  fitness curve was flat).
- Population[0] is the §9.3 hand-tuned seed individual so the curve is
  monotone-ish from generation 1 (R-4 mitigation at the algorithm level).
- Fitness now uses a side-effect-free in-memory simulator path. GA tuning does
  not need SQLite rows, forecasts, checkpoints, or obituaries; those are built
  later by ``make build-grid`` using the winning policy.
- Islands + migration + elitism keep population diversity, and early stopping
  exits once best fitness has plateaued.
- Random immigrants and adaptive diversity rescue prevent island collapse
  (the failure mode observed in dry-runs where std→0 by generation ~10).
"""

from __future__ import annotations

import csv
import os
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta
from typing import List

from engine import api as engine
from engine.contracts import ComponentId, ComponentStatus
from sim.config import SimulationConfig
from sim.drivers.factory import build_drivers
from sim.loop import SIM_START_TIME, _apply_maintenance, _apply_maintenance_memory
from sim.policies import AIPolicy


# Constants — PLAN-B §9.1
POP_SIZE = int(os.environ.get("GA_POP_SIZE", "32"))
N_GEN = int(os.environ.get("GA_N_GEN", "20"))
TOURNAMENT = 3
ALPHA = 0.5
SIGMA = 0.05
MUT_PROB = 0.2
CX_PROB = 0.5
LAMBDA_COST = 1.5
LAMBDA_FAILURE = 50.0
NUM_ISLANDS = int(os.environ.get("GA_NUM_ISLANDS", "4"))
MIGRATION_INTERVAL = int(os.environ.get("GA_MIGRATION_INTERVAL", "4"))
EARLY_STOP_PATIENCE = int(os.environ.get("GA_EARLY_STOP_PATIENCE", "5"))
RANDOM_IMMIGRANT_RATE = float(os.environ.get("GA_RANDOM_IMMIGRANT_RATE", "0.15"))
DIVERSITY_FLOOR = float(os.environ.get("GA_DIVERSITY_FLOOR", "1.0"))
GA_WORKERS = int(
    os.environ.get(
        "GA_WORKERS",
        str(max(1, (os.cpu_count() or 2) - 2)),
    )
)
GA_TIME_STEP_MINUTES = int(os.environ.get("GA_TIME_STEP_MINUTES", "1"))
GA_HORIZON_MINUTES = int(os.environ.get("GA_HORIZON_MINUTES", "600"))

GA_TMP_DB = "data/ga_tmp.db"
GA_FITNESS_CSV = "data/ga_fitness.csv"
POLICIES_YAML = "config/policies.yaml"

# §9.3 hand-tuned seed individual: blade, motor, nozzle, resistor, heater, insulation, lookahead
SEED_INDIVIDUAL: List[float] = [0.50, 0.55, 0.45, 0.50, 0.55, 0.40, 0.30]

# Extra seeds preserve useful regions discovered in dry-runs. They are still
# evolved by the GA; they just prevent every island from starting as pure noise.
SEED_BANK: tuple[tuple[float, ...], ...] = (
    tuple(SEED_INDIVIDUAL),
    (0.30, 0.33, 0.29, 0.26, 0.32, 0.48, 0.0),
    (0.30, 0.33, 0.29, 0.26, 0.27, 0.48, 0.0),
    (0.3740, 0.3945, 0.2960, 0.1685, 0.1750, 0.3312, 0.0),
    (0.25, 0.24, 0.33, 0.47, 0.34, 0.14, 0.0),
    (0.20, 0.35, 0.25, 0.40, 0.35, 0.25, 0.0),
)

# Fixed gene order — used both to construct the AIPolicy thresholds dict and
# to write back the winning policy.
GENE_ORDER = (
    ComponentId.BLADE,
    ComponentId.MOTOR,
    ComponentId.NOZZLE,
    ComponentId.RESISTOR,
    ComponentId.HEATER,
    ComponentId.INSULATION,
)


def _individual_to_thresholds(individual) -> tuple[dict, float]:
    thresholds = {GENE_ORDER[i]: float(individual[i]) for i in range(6)}
    lookahead = float(individual[6])
    return thresholds, lookahead


def _evaluate(individual) -> tuple[float]:
    """Run a stressed-scenario simulation under this individual's policy and
    score it via uptime − λ_cost·maintenance − λ_failure·failures.

    This is the GA-specific fast path: it evaluates in memory and intentionally
    skips SQLite, forecast persistence, checkpoints, and obituaries. The final
    demo historian is still produced later by ``build-grid`` from the winning
    ``config/policies.yaml``.
    """
    thresholds, lookahead = _individual_to_thresholds(individual)

    cfg = SimulationConfig(
        scenario_name="stressed",
        policy="ai",
        seed=42,
        time_step_minutes=GA_TIME_STEP_MINUTES,
        horizon_minutes=GA_HORIZON_MINUTES,
        thresholds=thresholds,
        lookahead_coef=lookahead,
        config_json={
            "thresholds": {cid.value: thresholds[cid] for cid in GENE_ORDER},
            "lookahead": lookahead,
        },
    )

    state = engine.initial_state(cfg.scenario_name, cfg.seed)
    drivers_provider = build_drivers(cfg)
    policy = AIPolicy(thresholds=thresholds, lookahead_coef=lookahead)
    maintenance_clock: dict[ComponentId, object] = {}
    failed_components: set[ComponentId] = set()
    maintenance_count = 0
    uptime_minutes = 0

    t = SIM_START_TIME
    end = t + timedelta(minutes=cfg.horizon_minutes)
    while t < end:
        drivers = drivers_provider.get(t, cfg.scenario_name, cfg.seed)
        state = engine.step(state, drivers, cfg.time_step_minutes)
        state = _apply_maintenance_memory(state, maintenance_clock, t)

        if all(c.status != ComponentStatus.FAILED for c in state.components.values()):
            uptime_minutes += cfg.time_step_minutes
        failed_components.update(
            cid
            for cid, comp in state.components.items()
            if comp.status == ComponentStatus.FAILED
        )

        action_cid = policy.decide(state, t)
        if action_cid is not None:
            state = _apply_maintenance(state, action_cid)
            maintenance_clock[action_cid] = t
            maintenance_count += 1

        t += timedelta(minutes=cfg.time_step_minutes)

    uptime_hours = uptime_minutes / 60.0
    return (
        uptime_hours
        - LAMBDA_COST * maintenance_count
        - LAMBDA_FAILURE * len(failed_components),
    )


def _evaluate_score(genome: list[float]) -> float:
    return _evaluate(genome)[0]


def _build_toolbox():
    from deap import base, creator, tools  # type: ignore

    if "FitnessMax" not in creator.__dict__:
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if "Individual" not in creator.__dict__:
        creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()
    toolbox.register("attr_float", random.uniform, 0.1, 0.9)
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_float,
        n=7,
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", _evaluate)
    toolbox.register("mate", tools.cxBlend, alpha=ALPHA)
    toolbox.register(
        "mutate",
        tools.mutGaussian,
        mu=0,
        sigma=SIGMA,
        indpb=MUT_PROB,
    )
    toolbox.register("select", tools.selTournament, tournsize=TOURNAMENT)
    return toolbox, creator


def _seed_islands(toolbox, creator, total_pop: int, n_islands: int):
    """Create multiple populations with one useful seed per early island."""
    n_islands = max(1, min(n_islands, total_pop))
    base_size = max(1, total_pop // n_islands)
    remainder = total_pop % n_islands
    islands = []
    for i in range(n_islands):
        size = base_size + (1 if i < remainder else 0)
        pop = toolbox.population(n=size)
        if pop and i < len(SEED_BANK):
            pop[0] = creator.Individual(list(SEED_BANK[i]))
        islands.append(pop)
    return islands


def _evaluate_population(individuals: list) -> None:
    invalid = [ind for ind in individuals if not ind.fitness.valid]
    if not invalid:
        return
    genomes = [list(ind) for ind in invalid]
    workers = max(1, min(GA_WORKERS, len(genomes)))
    if workers == 1:
        scores = [_evaluate_score(genome) for genome in genomes]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            scores = list(pool.map(_evaluate_score, genomes))
    for ind, score in zip(invalid, scores):
        ind.fitness.values = (score,)


def _clone_individual(creator, ind):
    clone = creator.Individual(list(ind))
    if ind.fitness.valid:
        clone.fitness.values = ind.fitness.values
    return clone


def _migrate(islands: list, creator, tools) -> None:
    if len(islands) < 2:
        return
    bests = [tools.selBest(island, 1)[0] for island in islands if island]
    if len(bests) < 2:
        return
    for idx, island in enumerate(islands):
        if not island:
            continue
        incoming = bests[idx - 1]
        worst_idx = min(
            range(len(island)),
            key=lambda i: island[i].fitness.values[0],
        )
        island[worst_idx] = _clone_individual(creator, incoming)


def _inject_random_immigrants(
    island: list,
    toolbox,
    creator,
    *,
    rate: float,
) -> None:
    """Replace the worst non-elite individuals with fresh random genomes."""
    if len(island) <= 2 or rate <= 0:
        return
    n = max(1, int(round(len(island) * rate)))
    n = min(n, len(island) - 1)
    ranked = sorted(
        range(len(island)),
        key=lambda i: island[i].fitness.values[0],
    )
    # Preserve at least the current island champion.
    champion = tools_sel_best_index(island)
    targets = [idx for idx in ranked if idx != champion][:n]
    for idx in targets:
        island[idx] = creator.Individual(toolbox.individual())


def tools_sel_best_index(island: list) -> int:
    return max(range(len(island)), key=lambda i: island[i].fitness.values[0])


def _select_with_elite(toolbox, tools, creator, candidates: list, size: int) -> list:
    elite = tools.selBest(candidates, 1)[0]
    selected = toolbox.select(candidates, k=max(0, size - 1))
    out = [_clone_individual(creator, elite)]
    out.extend(_clone_individual(creator, ind) for ind in selected[: size - 1])
    return out


def _write_policies_yaml(
    best_individual,
    best_fitness: float,
    gen: int,
    path: str = POLICIES_YAML,
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write("# config/policies.yaml — generated by GA, do not hand-edit\n")
        fh.write("ai_policy:\n")
        fh.write("  thresholds:\n")
        for i, cid in enumerate(GENE_ORDER):
            fh.write(f"    {cid.value}: {best_individual[i]:.4f}\n")
        fh.write(f"  lookahead_coef: {best_individual[6]:.4f}\n")
        fh.write('  trained_on: "stressed-seed0042"\n')
        fh.write(f"  ga_generation: {gen}\n")
        fh.write(f"  best_fitness: {best_fitness:.4f}\n")


def run_ga(seed: int = 42) -> tuple[list, float]:
    """Main GA loop. Returns (best_individual, best_fitness).

    Deterministic for a given seed: same seed → same final individual to 8
    decimals (NFR-8 / §9.7 ``test_ga_determinism``).
    """
    from deap import algorithms, tools  # type: ignore

    random.seed(seed)
    toolbox, creator = _build_toolbox()

    islands = _seed_islands(toolbox, creator, POP_SIZE, NUM_ISLANDS)

    # Initial evaluation
    for island in islands:
        _evaluate_population(island)

    os.makedirs(os.path.dirname(GA_FITNESS_CSV), exist_ok=True)
    with open(GA_FITNESS_CSV, "w", newline="") as fh:
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

        best_seen = float("-inf")
        best_ind = None
        stale_generations = 0
        final_gen = 0

        for gen in range(N_GEN):
            island_offspring = []
            all_offspring = []
            for island_idx, island in enumerate(islands):
                if not island:
                    island_offspring.append((island_idx, []))
                    continue
                offspring = algorithms.varAnd(
                    island, toolbox, cxpb=CX_PROB, mutpb=MUT_PROB
                )
                # Clamp genes to [0, 1] after mutation (mutGaussian can drift out).
                for ind in offspring:
                    for i in range(len(ind)):
                        ind[i] = max(0.0, min(1.0, ind[i]))
                island_offspring.append((island_idx, offspring))
                all_offspring.extend(offspring)

            # Evaluate the whole generation in one worker pool so every core
            # stays busy and we do not pay process startup once per island.
            _evaluate_population(all_offspring)

            all_parent_scores = [
                ind.fitness.values[0] for island in islands for ind in island
            ]
            diversity = (
                statistics.stdev(all_parent_scores)
                if len(all_parent_scores) > 1
                else 0.0
            )
            immigrant_rate = RANDOM_IMMIGRANT_RATE
            if diversity < DIVERSITY_FLOOR:
                immigrant_rate = min(0.35, RANDOM_IMMIGRANT_RATE * 2.0)

            for island_idx, offspring in island_offspring:
                island = islands[island_idx]
                if not island:
                    continue
                # Elitism: preserve the island champion so one bad generation
                # cannot wipe out the best-known genome.
                candidates = offspring + [_clone_individual(creator, tools.selBest(island, 1)[0])]
                islands[island_idx] = _select_with_elite(
                    toolbox, tools, creator, candidates, len(island)
                )
                _inject_random_immigrants(
                    islands[island_idx],
                    toolbox,
                    creator,
                    rate=immigrant_rate,
                )

            # Immigrants are new individuals; evaluate them before migration
            # and stats so the CSV reflects actual fitness values.
            for island in islands:
                _evaluate_population(island)

            if MIGRATION_INTERVAL > 0 and (gen + 1) % MIGRATION_INTERVAL == 0:
                _migrate(islands, creator, tools)

            all_individuals = [ind for island in islands for ind in island]
            scores = [ind.fitness.values[0] for ind in all_individuals]
            current_best = max(scores)
            current_best_ind = tools.selBest(all_individuals, 1)[0]
            writer.writerow(
                {
                    "generation": gen,
                    "best_fitness": current_best,
                    "mean_fitness": statistics.mean(scores),
                    "std_fitness": (
                        statistics.stdev(scores) if len(scores) > 1 else 0.0
                    ),
                }
            )
            fh.flush()

            final_gen = gen + 1
            if current_best > best_seen + 1e-9:
                best_seen = current_best
                best_ind = _clone_individual(creator, current_best_ind)
                stale_generations = 0
            else:
                stale_generations += 1
            if stale_generations >= EARLY_STOP_PATIENCE:
                break

    if best_ind is None:
        all_individuals = [ind for island in islands for ind in island]
        best_ind = tools.selBest(all_individuals, 1)[0]
        best_seen = best_ind.fitness.values[0]

    # Pass POLICIES_YAML explicitly so monkeypatched values during testing
    # are honored (default args are bound at function-definition time).
    _write_policies_yaml(best_ind, best_seen, final_gen, path=POLICIES_YAML)
    return list(best_ind), float(best_seen)


if __name__ == "__main__":  # pragma: no cover
    run_ga()
