"""ThermalFiringResistors tests — PLAN-A §6.5."""

from __future__ import annotations

import numpy as np

from engine.components import ThermalFiringResistors
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


def _dh(resistor: ThermalFiringResistors, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return resistor.intrinsic_decay(isolated_state(ComponentId.RESISTOR, h), drivers, 1.0, rng)


def test_resistor_driver_dependent_change():
    """Higher temp_C and lower voltage_stability -> larger Coffin-Manson swing."""
    res = ThermalFiringResistors()
    base = make_drivers(temp_C=25.0, voltage_stability=1.0)
    higher = make_drivers(temp_C=80.0, voltage_stability=0.4)
    assert abs(_dh(res, higher)) > abs(_dh(res, base))


def test_resistor_health_clamped_0_1():
    res = ThermalFiringResistors()
    healths = iterate_intrinsic(res, stressed_drivers, minutes=600, seed=29)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_resistor_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_resistor_metrics_keys_present():
    res = ThermalFiringResistors()
    keys = set(
        res.emit_metrics(isolated_state(ComponentId.RESISTOR, 0.5), make_drivers()).keys()
    )
    assert keys == {"resistance_pct"}


def test_resistor_determinism():
    res = ThermalFiringResistors()
    drivers = make_drivers(temp_C=50.0, voltage_stability=0.7)
    rng_a = np.random.default_rng(2)
    rng_b = np.random.default_rng(2)
    state = isolated_state(ComponentId.RESISTOR, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.RESISTOR,
        health=max(0.0, min(1.0, 0.6 + res.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=res.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.RESISTOR,
        health=max(0.0, min(1.0, 0.6 + res.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=res.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()
