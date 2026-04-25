"""ExponentialDecay unit tests — PLAN-A §5.4."""

from __future__ import annotations

import numpy as np

from engine.failure_models import ExponentialDecay


def _rng() -> np.random.Generator:
    return np.random.default_rng(seed=0)


def test_known_input_known_output():
    """alpha=0.001, stress=1.0, H=1.0, dt=60 -> dH ~= -0.06 within 1e-9."""
    model = ExponentialDecay()
    dh = model.decay(
        health=1.0,
        drivers={"alpha": 0.001, "stress": 1.0},
        dt=60.0,
        rng=_rng(),
    )
    assert abs(dh - (-0.06)) < 1e-9


def test_zero_stress_no_decay():
    model = ExponentialDecay()
    dh = model.decay(
        health=0.5,
        drivers={"alpha": 0.001, "stress": 0.0},
        dt=60.0,
        rng=_rng(),
    )
    assert dh == 0.0
