"""DriveMotor tests — PLAN-A §6.5."""

from __future__ import annotations

import numpy as np

from engine.components import DriveMotor
from engine.contracts import ComponentId, ComponentState, ComponentStatus, status_for_health
from tests.engine.components._helpers import (
    isolated_state,
    iterate_intrinsic,
    make_drivers,
    stressed_drivers,
)


def _dh(motor: DriveMotor, drivers, h: float = 0.9, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return motor.intrinsic_decay(isolated_state(ComponentId.MOTOR, h), drivers, 1.0, rng)


def test_motor_driver_dependent_change():
    """Increasing operational hours (the dominant Weibull driver via t_eff)
    strictly increases |dH|."""
    motor = DriveMotor()
    base = make_drivers(hours=2.0, voltage_stability=0.8)
    higher = make_drivers(hours=8.0, voltage_stability=0.8)
    assert abs(_dh(motor, higher)) > abs(_dh(motor, base))


def test_motor_health_clamped_0_1():
    motor = DriveMotor()
    healths = iterate_intrinsic(motor, stressed_drivers, minutes=600, seed=11)
    assert all(0.0 <= h <= 1.0 for h in healths)


def test_motor_status_thresholds():
    for h, expected in [
        (0.71, ComponentStatus.FUNCTIONAL),
        (0.69, ComponentStatus.DEGRADED),
        (0.41, ComponentStatus.DEGRADED),
        (0.39, ComponentStatus.CRITICAL),
        (0.11, ComponentStatus.CRITICAL),
        (0.09, ComponentStatus.FAILED),
    ]:
        assert status_for_health(h) == expected


def test_motor_metrics_keys_present():
    motor = DriveMotor()
    keys = set(
        motor.emit_metrics(isolated_state(ComponentId.MOTOR, 0.5), make_drivers()).keys()
    )
    assert keys == {"current_draw_A", "bearing_temp_C"}


def test_motor_determinism():
    motor = DriveMotor()
    drivers = make_drivers(hours=4.0, voltage_stability=0.7, cycles=400)
    rng_a = np.random.default_rng(3)
    rng_b = np.random.default_rng(3)
    state = isolated_state(ComponentId.MOTOR, 0.6)
    s1 = ComponentState(
        component_id=ComponentId.MOTOR,
        health=max(0.0, min(1.0, 0.6 + motor.intrinsic_decay(state, drivers, 1.0, rng_a))),
        status=ComponentStatus.DEGRADED,
        metrics=motor.emit_metrics(state, drivers),
    )
    s2 = ComponentState(
        component_id=ComponentId.MOTOR,
        health=max(0.0, min(1.0, 0.6 + motor.intrinsic_decay(state, drivers, 1.0, rng_b))),
        status=ComponentStatus.DEGRADED,
        metrics=motor.emit_metrics(state, drivers),
    )
    assert s1.model_dump_json() == s2.model_dump_json()
