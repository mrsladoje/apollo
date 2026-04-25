"""HeatingElement tests — PLAN-A §6.5 + heater-specific PINN-call assertion."""

from __future__ import annotations

from typing import List

import numpy as np

from engine.components import HeatingElement
from engine.components.heater import _SAMPLE_X
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from engine.pinn.inference import HeaterPINN
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


class _SpyPINN:
    """Minimal mock that records each forward call. Returns a deterministic
    field shaped like the real PINN's output, so the heater integrates without
    surprises during the assertion."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        self.calls.append((np.asarray(x).copy(), float(t)))
        x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
        # Linear profile from 200 degC to 25 degC over the rod.
        return 25.0 + (200.0 - 25.0) * (1.0 - x_arr / x_arr[-1])


def _dh(heater: HeatingElement, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return heater.intrinsic_decay(isolated_state(ComponentId.HEATER, h), drivers, 1.0, rng)


def test_heater_driver_dependent_change():
    heater = HeatingElement(pinn=_SpyPINN())
    base = make_drivers(temp_C=25.0, voltage_stability=1.0, hours=1.0)
    higher = make_drivers(temp_C=70.0, voltage_stability=0.3, hours=1.0)
    assert abs(_dh(heater, higher)) > abs(_dh(heater, base))


def test_heater_health_clamped_0_1():
    heater = HeatingElement(pinn=_SpyPINN())
    healths = iterate_intrinsic(heater, stressed_drivers, minutes=600, seed=37)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_heater_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_heater_metrics_keys_present():
    heater = HeatingElement(pinn=_SpyPINN())
    keys = set(
        heater.emit_metrics(isolated_state(ComponentId.HEATER, 0.5), make_drivers()).keys()
    )
    assert keys == {"temp_x0_C", "temp_xmid_C", "temp_xL_C", "drift_pct"}


def test_heater_determinism():
    heater_a = HeatingElement(pinn=_SpyPINN())
    heater_b = HeatingElement(pinn=_SpyPINN())
    drivers = make_drivers(temp_C=50.0, voltage_stability=0.7, hours=2.0)
    rng_a = np.random.default_rng(13)
    rng_b = np.random.default_rng(13)
    state = isolated_state(ComponentId.HEATER, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.HEATER,
        health=max(0.0, min(1.0, 0.6 + heater_a.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=heater_a.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.HEATER,
        health=max(0.0, min(1.0, 0.6 + heater_b.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=heater_b.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()


def test_heater_pinn_called_each_step():
    """Patch the PINN object, assert __call__ invoked once per step (§6.5)."""
    spy = _SpyPINN()
    heater = HeatingElement(pinn=spy)
    drivers = make_drivers(temp_C=40.0, hours=1.0)
    state = isolated_state(ComponentId.HEATER, 0.8)
    rng = np.random.default_rng(0)
    n_decay = 5
    for _ in range(n_decay):
        heater.intrinsic_decay(state, drivers, 1.0, rng)
    # intrinsic_decay invokes the PINN exactly once per call.
    assert len(spy.calls) == n_decay
    last_x, _ = spy.calls[-1]
    assert np.allclose(last_x, _SAMPLE_X)
