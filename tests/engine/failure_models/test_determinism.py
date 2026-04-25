"""Failure-model determinism — PLAN-A §5.4 (FR-1.5, NFR-1)."""

from __future__ import annotations

import numpy as np

from engine.failure_models import CoffinManson, ExponentialDecay, WeibullDecay


def _run_all_three(seed: int) -> tuple:
    rng_a = np.random.default_rng(seed)
    rng_b = np.random.default_rng(seed)
    rng_c = np.random.default_rng(seed)

    expo = ExponentialDecay().decay(
        health=0.8,
        drivers={"alpha": 1e-3, "stress": 0.7},
        dt=5.0,
        rng=rng_a,
    )
    weib = WeibullDecay().decay(
        health=0.8,
        drivers={"beta": 2.0, "eta": 1000.0, "t": 250.0},
        dt=5.0,
        rng=rng_b,
    )
    cm = CoffinManson().decay(
        health=0.8,
        drivers={"C": 1e6, "c": 2.0, "delta_eps": 0.004, "cycles_this_step": 7.0},
        dt=5.0,
        rng=rng_c,
    )
    return expo, weib, cm


def test_two_runs_byte_identical():
    a = _run_all_three(seed=42)
    b = _run_all_three(seed=42)
    assert a == b
