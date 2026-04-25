"""WeibullDecay unit tests — PLAN-A §5.4."""

from __future__ import annotations

import numpy as np

from engine.failure_models import WeibullDecay


def _rng() -> np.random.Generator:
    return np.random.default_rng(seed=0)


def test_known_input_known_output():
    """beta=2.5, eta=400, t=200, dt=1 reproduces closed-form hazard to 1e-9."""
    beta, eta, t, dt = 2.5, 400.0, 200.0, 1.0
    expected_hazard = (beta / eta) * (t / eta) ** (beta - 1.0)
    expected_dh = -expected_hazard * dt

    model = WeibullDecay()
    dh = model.decay(
        health=1.0,
        drivers={"beta": beta, "eta": eta, "t": t},
        dt=dt,
        rng=_rng(),
    )
    assert abs(dh - expected_dh) < 1e-9


def test_hazard_monotone_increasing():
    """For beta > 1, h(t2) > h(t1) for t2 > t1 over 100 sample times."""
    model = WeibullDecay()
    beta, eta = 2.5, 400.0
    times = np.linspace(1.0, 1000.0, 100)
    last = -np.inf
    for t in times:
        dh = model.decay(
            health=1.0,
            drivers={"beta": beta, "eta": eta, "t": float(t)},
            dt=1.0,
            rng=_rng(),
        )
        # hazard = -dh / dt, must strictly increase
        hazard = -dh / 1.0
        assert hazard > last
        last = hazard
