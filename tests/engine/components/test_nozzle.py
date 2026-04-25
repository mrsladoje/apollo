"""NozzlePlate tests — PLAN-A §6.5."""

from __future__ import annotations

import numpy as np

from engine.components import NozzlePlate
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


def _dh(nozzle: NozzlePlate, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return nozzle.intrinsic_decay(isolated_state(ComponentId.NOZZLE, h), drivers, 1.0, rng)


def test_nozzle_driver_dependent_change():
    nozzle = NozzlePlate()
    base = make_drivers(humidity=0.3, hours=2.0)
    higher = make_drivers(humidity=0.85, hours=2.0)
    assert abs(_dh(nozzle, higher)) > abs(_dh(nozzle, base))


def test_nozzle_health_clamped_0_1():
    nozzle = NozzlePlate()
    healths = iterate_intrinsic(nozzle, stressed_drivers, minutes=600, seed=23)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_nozzle_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_nozzle_metrics_keys_present():
    nozzle = NozzlePlate()
    keys = set(
        nozzle.emit_metrics(isolated_state(ComponentId.NOZZLE, 0.5), make_drivers()).keys()
    )
    assert keys == {"clog_prob", "active_nozzle_count"}


def test_nozzle_determinism():
    nozzle = NozzlePlate()
    drivers = make_drivers(humidity=0.7, temp_C=40.0, hours=3.0)
    rng_a = np.random.default_rng(5)
    rng_b = np.random.default_rng(5)
    state = isolated_state(ComponentId.NOZZLE, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.NOZZLE,
        health=max(0.0, min(1.0, 0.6 + nozzle.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=nozzle.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.NOZZLE,
        health=max(0.0, min(1.0, 0.6 + nozzle.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=nozzle.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()


def test_nozzle_humidity_drives_clog():
    """Humidity 0.3 -> 0.8 increases the dH derivative by >= 1.5x — §6.5."""
    nozzle = NozzlePlate()
    low = make_drivers(humidity=0.3, hours=2.0)
    high = make_drivers(humidity=0.8, hours=2.0)
    assert abs(_dh(nozzle, high)) >= 1.5 * abs(_dh(nozzle, low))
