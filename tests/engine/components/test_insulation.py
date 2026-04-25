"""InsulationPanel tests — PLAN-A §6.5."""

from __future__ import annotations

import numpy as np

from engine.components import InsulationPanel
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


def _dh(insul: InsulationPanel, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return insul.intrinsic_decay(isolated_state(ComponentId.INSULATION, h), drivers, 1.0, rng)


def test_insulation_driver_dependent_change():
    insul = InsulationPanel()
    base = make_drivers(temp_C=30.0)
    higher = make_drivers(temp_C=80.0)
    assert abs(_dh(insul, higher)) > abs(_dh(insul, base))


def test_insulation_health_clamped_0_1():
    insul = InsulationPanel()
    healths = iterate_intrinsic(insul, stressed_drivers, minutes=600, seed=41)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_insulation_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_insulation_metrics_keys_present():
    insul = InsulationPanel()
    keys = set(
        insul.emit_metrics(isolated_state(ComponentId.INSULATION, 0.5), make_drivers()).keys()
    )
    assert keys == {"k_eff_W_mK"}


def test_insulation_determinism():
    insul = InsulationPanel()
    drivers = make_drivers(temp_C=60.0)
    rng_a = np.random.default_rng(8)
    rng_b = np.random.default_rng(8)
    state = isolated_state(ComponentId.INSULATION, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.INSULATION,
        health=max(0.0, min(1.0, 0.6 + insul.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=insul.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.INSULATION,
        health=max(0.0, min(1.0, 0.6 + insul.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=insul.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()
