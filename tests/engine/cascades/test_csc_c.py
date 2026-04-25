"""CSC-C — Powder contamination loop tests — PLAN-A §7.4."""

from __future__ import annotations

import numpy as np

from engine.components import NozzlePlate
from engine.contracts import ComponentId, ROW_ORDER
from engine.coupling import apply_coupling
from tests.engine.components._helpers import isolated_state, make_drivers


def _step_nozzle(blade_h: float, *, minutes: int = 60, nozzle_h: float = 0.95) -> float:
    """Nozzle decay over `minutes` under fixed blade health (matrix-only path)."""
    nozzle = NozzlePlate()
    rng = np.random.default_rng(0)
    blade_idx = ROW_ORDER.index(ComponentId.BLADE)
    nozzle_idx = ROW_ORDER.index(ComponentId.NOZZLE)
    healths = np.ones(6)
    healths[blade_idx] = blade_h
    healths[nozzle_idx] = nozzle_h

    drivers = make_drivers(humidity=0.5, hours=2.0, temp_C=25.0)
    for _ in range(minutes):
        intrinsic = np.zeros(6)
        intrinsic[nozzle_idx] = nozzle.intrinsic_decay(
            isolated_state(ComponentId.NOZZLE, healths[nozzle_idx]),
            drivers,
            1.0,
            rng,
        )
        healths = apply_coupling(healths, intrinsic, dt=1.0)
        healths[blade_idx] = blade_h
    return float(nozzle_h - healths[nozzle_idx])


def test_csc_c_nozzle_accelerates_on_blade_flaking():
    dh_flaking = _step_nozzle(blade_h=0.1)
    dh_healthy = _step_nozzle(blade_h=1.0)
    assert dh_flaking >= 1.5 * max(dh_healthy, 1e-9)
