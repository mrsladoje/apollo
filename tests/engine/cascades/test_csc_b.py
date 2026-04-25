"""CSC-B — Thermal-Printhead loop tests — PLAN-A §7.4."""

from __future__ import annotations

import math

import numpy as np

from engine.cascades import csc_b
from engine.components import (
    DriveMotor,
    HeatingElement,
    InsulationPanel,
    NozzlePlate,
    RecoaterBlade,
    ThermalFiringResistors,
)
from engine.contracts import ComponentId, ROW_ORDER, ComponentStatus, status_for_health
from engine.coupling import apply_coupling
from tests.engine.components._helpers import isolated_state, stressed_drivers


def test_csc_b_arrhenius_monotone():
    """binder_viscosity(50) > binder_viscosity(30); ratio matches Arrhenius."""
    mu30 = csc_b.binder_viscosity(30.0)
    mu50 = csc_b.binder_viscosity(50.0)
    assert mu50 > mu30
    expected_ratio = math.exp(
        csc_b.EA_OVER_R * (1.0 / (30.0 + 273.15) - 1.0 / (50.0 + 273.15))
    )
    assert abs(mu50 / mu30 - expected_ratio) < 1e-6


def test_csc_b_coffin_manson_damage_monotone_in_dt():
    """Damage strictly increases with delta_T for fixed cycles."""
    cycles = 100.0
    deltas = [10.0, 25.0, 50.0, 100.0, 200.0]
    damages = [csc_b.coffin_manson_damage(dT, cycles) for dT in deltas]
    for a, b in zip(damages[:-1], damages[1:]):
        assert b > a


def _run_full_engine(*, insulation_h0: float, minutes: int, seed: int = 42) -> int:
    """Iterate the full 6-component engine. Return first minute (>=0) at which
    the nozzle reaches CRITICAL, or `minutes` if it never does."""
    blade = RecoaterBlade()
    motor = DriveMotor()
    nozzle = NozzlePlate()
    resistor = ThermalFiringResistors()
    heater = HeatingElement()
    insul = InsulationPanel()

    components = {
        ComponentId.BLADE: blade,
        ComponentId.MOTOR: motor,
        ComponentId.NOZZLE: nozzle,
        ComponentId.RESISTOR: resistor,
        ComponentId.HEATER: heater,
        ComponentId.INSULATION: insul,
    }

    healths = np.ones(6, dtype=np.float64)
    healths[ROW_ORDER.index(ComponentId.INSULATION)] = insulation_h0

    rng = np.random.default_rng(seed)
    nozzle_idx = ROW_ORDER.index(ComponentId.NOZZLE)
    insul_idx = ROW_ORDER.index(ComponentId.INSULATION)
    crit_at = minutes

    for t in range(minutes):
        drivers = stressed_drivers(t, rng_seed=seed)
        intrinsic = np.zeros(6, dtype=np.float64)
        for cid, comp in components.items():
            idx = ROW_ORDER.index(cid)
            state = isolated_state(cid, healths[idx])
            intrinsic[idx] = comp.intrinsic_decay(state, drivers, 1.0, rng)
        healths = apply_coupling(healths, intrinsic, dt=1.0)
        # Pin insulation health (the test isolates the CSC-B downstream
        # effect of a chronically-degraded insulation panel).
        healths[insul_idx] = insulation_h0

        # Layer CSC-B physics on top of the matrix coupling.
        field = heater._temp_field(drivers)
        swing = float(np.max(field) - np.min(field))
        healths = csc_b.apply_csc_b(
            healths,
            heater_temp_swing_K=swing,
            enclosure_temp_C=drivers.temp_C,
            duty_cycles_this_step=heater.duty_cycles_per_min,
            dt=1.0,
        )

        if (
            crit_at == minutes
            and status_for_health(float(healths[nozzle_idx])) == ComponentStatus.CRITICAL
        ):
            crit_at = t
    return crit_at


def test_csc_b_full_path():
    """Stressed scenario, 600 min: nozzle reaches CRITICAL strictly earlier
    when insulation is chronically degraded (h=0.6) vs healthy (h=1.0)."""
    crit_degraded = _run_full_engine(insulation_h0=0.6, minutes=600)
    crit_healthy = _run_full_engine(insulation_h0=1.0, minutes=600)
    assert crit_degraded < crit_healthy
