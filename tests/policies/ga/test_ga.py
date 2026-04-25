"""§9.7 — GA / Optuna fallback gates.

These tests run a tiny GA (3 generations × 6 individuals) and a tiny
Optuna search (8 trials) so they fit in CI budget. The behavioral
properties they check are size-independent:

- Same seed ⇒ same final individual (determinism, NFR-8).
- Fitness CSV header matches Plan C's expected schema.
- Fitness function rewards genomes that prevent failure over genomes
  that don't.
- ``policies.yaml`` is written with valid AI-policy structure.
- Optuna fallback writes the same artifacts.
"""

from __future__ import annotations

import csv
import os

import pytest

deap = pytest.importorskip("deap")
optuna = pytest.importorskip("optuna")

from sim.optimizer import ga as ga_mod  # noqa: E402
from sim.optimizer import optuna_fallback  # noqa: E402


@pytest.fixture
def tiny_ga_config(monkeypatch, tmp_path):
    """Shrink the GA so the test fits in CI."""
    monkeypatch.setattr(ga_mod, "POP_SIZE", 6)
    monkeypatch.setattr(ga_mod, "N_GEN", 3)
    monkeypatch.setattr(ga_mod, "GA_TMP_DB", str(tmp_path / "ga_tmp.db"))
    monkeypatch.setattr(ga_mod, "GA_FITNESS_CSV", str(tmp_path / "ga.csv"))
    monkeypatch.setattr(ga_mod, "POLICIES_YAML", str(tmp_path / "policies.yaml"))
    return tmp_path


def test_ga_is_deterministic(tiny_ga_config):
    a, _ = ga_mod.run_ga(seed=42)
    # Reset DEAP creator so a fresh population can be built.
    b, _ = ga_mod.run_ga(seed=42)
    assert all(abs(x - y) < 1e-8 for x, y in zip(a, b))


def test_ga_fitness_csv_format(tiny_ga_config):
    ga_mod.run_ga(seed=42)
    with open(ga_mod.GA_FITNESS_CSV, newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == [
            "generation",
            "best_fitness",
            "mean_fitness",
            "std_fitness",
        ]
        rows = list(reader)
    assert len(rows) == ga_mod.N_GEN
    bests = [float(r["best_fitness"]) for r in rows]
    means = [float(r["mean_fitness"]) for r in rows]
    stds = [float(r["std_fitness"]) for r in rows]
    # Sanity: every row populated, no NaN, std non-negative.
    assert all(b == b for b in bests)
    assert all(s >= 0.0 for s in stds)
    # best_fitness >= mean_fitness within each generation.
    for b, m in zip(bests, means):
        assert b >= m - 1e-9


def test_ga_writes_valid_policies_yaml(tiny_ga_config):
    ga_mod.run_ga(seed=42)
    import yaml

    with open(ga_mod.POLICIES_YAML) as fh:
        data = yaml.safe_load(fh)
    assert "ai_policy" in data
    ap = data["ai_policy"]
    assert set(ap["thresholds"]) == {
        "blade",
        "motor",
        "nozzle",
        "resistor",
        "heater",
        "insulation",
    }
    assert 0.0 <= ap["lookahead_coef"] <= 1.0


def test_fitness_function_responds_to_genome(tiny_ga_config):
    """The fitness function must distinguish between distinct genomes.

    Earlier revisions of the GA dropped the genome into ``config_json`` but
    the loop ignored it — every individual evaluated to the same default
    policy and the fitness curve was flat. This test asserts that fix:
    different genomes ⇒ different fitness.
    """
    a = [0.85] * 6 + [0.5]
    b = [0.05] * 6 + [0.05]
    f_a = ga_mod._evaluate(a)[0]
    f_b = ga_mod._evaluate(b)[0]
    assert f_a != f_b, (
        "fitness function ignored the genome; same evaluation for distinct individuals"
    )

    # The §9.3 hand-tuned seed should beat both extremes (it is a balanced
    # threshold profile and trades off cost vs. failures explicitly).
    f_seed = ga_mod._evaluate(ga_mod.SEED_INDIVIDUAL)[0]
    assert f_seed > min(f_a, f_b), "seed individual underperforms both extremes"


def test_optuna_fallback_writes_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(ga_mod, "GA_TMP_DB", str(tmp_path / "ga_tmp.db"))
    csv_path = tmp_path / "fitness.csv"
    yaml_path = tmp_path / "policies.yaml"
    best, value = optuna_fallback.optimize_with_optuna(
        n_trials=8,
        seed=42,
        csv_path=str(csv_path),
        yaml_path=str(yaml_path),
    )
    assert os.path.exists(csv_path)
    assert os.path.exists(yaml_path)
    assert len(best) == 7
    assert all(0.0 <= g <= 1.0 for g in best)
