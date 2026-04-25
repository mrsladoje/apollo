"""RecoaterBlade tests — PLAN-A §6.5."""

from __future__ import annotations

import numpy as np

from engine.components import RecoaterBlade
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


def _dh(blade: RecoaterBlade, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return blade.intrinsic_decay(isolated_state(ComponentId.BLADE, h), drivers, 1.0, rng)


def test_blade_driver_dependent_change():
    blade = RecoaterBlade()
    base = make_drivers(psd_d50=20.0, pm25=10.0, cycles=100)
    higher = make_drivers(psd_d50=40.0, pm25=10.0, cycles=100)
    assert abs(_dh(blade, higher)) > abs(_dh(blade, base))


def test_blade_health_clamped_0_1():
    blade = RecoaterBlade()
    healths = iterate_intrinsic(blade, stressed_drivers, minutes=600, seed=42)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_blade_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_blade_metrics_keys_present():
    blade = RecoaterBlade()
    state = isolated_state(ComponentId.BLADE, 0.5)
    keys = set(blade.emit_metrics(state, make_drivers(cycles=200)).keys())
    assert keys == {"blade_thickness_mm", "impact_count"}


def test_blade_determinism():
    blade = RecoaterBlade()
    drivers = make_drivers(psd_d50=30.0, pm25=20.0, cycles=500, hours=4.0)
    rng_a = np.random.default_rng(7)
    rng_b = np.random.default_rng(7)
    state = isolated_state(ComponentId.BLADE, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.BLADE,
        health=max(0.0, min(1.0, 0.6 + blade.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=blade.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.BLADE,
        health=max(0.0, min(1.0, 0.6 + blade.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=blade.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()


def test_blade_psd_d90_drives_wear():
    """D50 doubled (PRD-§9.2 names it psd_d50) drops thickness >= 1.8x faster
    over 60 minutes — PLAN-A §6.5 component-specific case."""
    blade = RecoaterBlade()
    healths_base = iterate_intrinsic(
        blade,
        lambda t: make_drivers(psd_d50=20.0, pm25=10.0, cycles=t),
        minutes=60,
        seed=0,
    )
    healths_doubled = iterate_intrinsic(
        blade,
        lambda t: make_drivers(psd_d50=40.0, pm25=10.0, cycles=t),
        minutes=60,
        seed=0,
    )
    drop_base = 1.0 - healths_base[-1]
    drop_doubled = 1.0 - healths_doubled[-1]
    assert drop_base > 0.0
    assert drop_doubled >= 1.8 * drop_base
