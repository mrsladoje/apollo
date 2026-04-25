"""CoffinManson unit tests — PLAN-A §5.4."""

from __future__ import annotations

import numpy as np

from engine.failure_models import CoffinManson


def _rng() -> np.random.Generator:
    return np.random.default_rng(seed=0)


def test_known_input_known_output():
    """C=1e6, c=2.0, delta_eps=0.005, cycles=10 -> dH = -10 / (1e6 * 0.005^-2) within 1e-12."""
    C, c, delta_eps, cycles = 1e6, 2.0, 0.005, 10.0
    expected_dh = -cycles / (C * (delta_eps ** -c))

    model = CoffinManson()
    dh = model.decay(
        health=1.0,
        drivers={"C": C, "c": c, "delta_eps": delta_eps, "cycles_this_step": cycles},
        dt=1.0,
        rng=_rng(),
    )
    assert abs(dh - expected_dh) < 1e-12


def test_zero_cycles_no_decay():
    model = CoffinManson()
    dh = model.decay(
        health=1.0,
        drivers={"C": 1e6, "c": 2.0, "delta_eps": 0.005, "cycles_this_step": 0.0},
        dt=1.0,
        rng=_rng(),
    )
    assert dh == 0.0
