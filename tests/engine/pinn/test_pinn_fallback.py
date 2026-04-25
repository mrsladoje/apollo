"""R-2 fallback: APOLLO_PINN_FALLBACK=1 swaps in a sklearn regressor — §8.8."""

from __future__ import annotations

import os

import numpy as np
import pytest

from engine.api import initial_state, step
from engine.contracts import ComponentId, Drivers
from engine.pinn.fallback import HeaterRegressor
from engine.pinn.inference import HeaterPINN


@pytest.fixture
def fallback_env(monkeypatch):
    monkeypatch.setenv("APOLLO_PINN_FALLBACK", "1")
    yield


def test_pinn_fallback_loadable(fallback_env):
    pinn = HeaterPINN()
    # The wrapper has wired the fallback; net is None, fallback is set.
    assert pinn._net is None
    assert pinn._fallback is not None
    out = pinn(np.array([0.0, 0.025, 0.05]), 0.5)
    assert out.shape == (3,)
    # Hot side > ambient side (boundary conditions are physically directed).
    assert out[0] > out[2]


def test_step_runs_with_fallback(fallback_env):
    state = initial_state(scenario="stressed", seed=1)
    drivers = Drivers(
        temp_C=40.0,
        humidity=0.7,
        pm25=20.0,
        psd_d50=25.0,
        voltage_stability=0.8,
        cycles=10,
        hours=0.2,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="day",
        rng_seed=1,
    )
    s1 = step(state, drivers, dt=1.0)
    assert set(s1.components.keys()) == set(ComponentId)


def test_fallback_regressor_is_loaded():
    fb = HeaterRegressor()
    assert fb._gbr is not None  # the trained pickle is on disk
