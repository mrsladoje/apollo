"""CSC-A — Recoating loop tests — PLAN-A §7.4."""

from __future__ import annotations

import numpy as np

from engine.components import DriveMotor
from engine.contracts import ComponentId, ROW_ORDER
from engine.coupling import apply_coupling
from tests.engine.components._helpers import isolated_state, make_drivers


def _step_motor(blade_h: float, *, minutes: int = 60, motor_h: float = 0.95) -> float:
    """Simulate `minutes` of motor evolution under a fixed blade health."""
    motor = DriveMotor()
    rng = np.random.default_rng(0)
    blade_idx = ROW_ORDER.index(ComponentId.BLADE)
    motor_idx = ROW_ORDER.index(ComponentId.MOTOR)
    healths = np.ones(6)
    healths[blade_idx] = blade_h
    healths[motor_idx] = motor_h

    drivers = make_drivers(hours=2.0, voltage_stability=0.8, cycles=200)
    for _ in range(minutes):
        intrinsic = np.zeros(6)
        intrinsic[motor_idx] = motor.intrinsic_decay(
            isolated_state(ComponentId.MOTOR, healths[motor_idx]),
            drivers,
            1.0,
            rng,
        )
        # Hold blade fixed to isolate the matrix-only CSC-A effect.
        healths = apply_coupling(healths, intrinsic, dt=1.0)
        healths[blade_idx] = blade_h
    return float(motor_h - healths[motor_idx])


def test_csc_a_motor_accelerates_on_blade_failure():
    dh_unhealthy = _step_motor(blade_h=0.1)
    dh_healthy = _step_motor(blade_h=1.0)
    assert dh_unhealthy >= 1.5 * max(dh_healthy, 1e-9)
