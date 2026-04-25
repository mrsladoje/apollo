"""Heating Element — PLAN-A §6.3 row 5, ADR-005, ADR-006.

Wraps the DeepXDE PINN (`engine.pinn.inference.HeaterPINN`) — the only
neural model in the engine (ADR-001). The PINN predicts T(x, t) on a
1-D rod; we sample three points (x0, xmid, xL) per step. The Coffin-Manson
fatigue layer reads the predicted swing and accumulates damage.
Drivers: temp_C, hours, voltage_stability. Metrics:
predicted_temp_field_x0_C, predicted_temp_field_xmid_C,
predicted_temp_field_xL_C, drift_pct.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import CoffinManson
from engine.pinn.inference import HeaterPINN, L_ROD


# Three sample points per §6.3 (PLAN-A). Stable across runs (NFR-1).
_SAMPLE_X = np.array([0.0, L_ROD * 0.5, L_ROD], dtype=np.float64)


class HeatingElement(Component):
    component_id = ComponentId.HEATER
    intrinsic_alpha: float = 1.0

    cm_C: float = 1.0e3
    cm_c: float = 2.0
    alpha_tc: float = 1.5e-5
    duty_cycles_per_min: float = 30.0

    def __init__(self, pinn: Optional[HeaterPINN] = None) -> None:
        self._cm = CoffinManson()
        self._pinn = pinn if pinn is not None else HeaterPINN()

    def _t_seconds(self, drivers: Drivers) -> float:
        # The PINN's "t" is seconds since the duty pulse started; we wrap to
        # [0, 60s] per minute to keep the predicted field bounded.
        return float((drivers.hours * 3600.0) % 60.0)

    def _temp_field(self, drivers: Drivers) -> np.ndarray:
        t_s = self._t_seconds(drivers)
        return np.asarray(self._pinn(_SAMPLE_X, t_s), dtype=np.float64)

    def _delta_T(self, field: np.ndarray) -> float:
        return float(np.max(field) - np.min(field))

    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        field = self._temp_field(drivers)
        return self.intrinsic_decay_from_field(state, drivers, dt, rng, field)

    def intrinsic_decay_from_field(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
        field: np.ndarray,
    ) -> float:
        delta_T = max(1.0, self._delta_T(field))
        instab = 1.0 - max(0.0, min(1.0, drivers.voltage_stability))
        cycles = self.duty_cycles_per_min * dt * (1.0 + 0.5 * instab)
        delta_eps = self.alpha_tc * delta_T
        return self._cm.decay(
            state.health,
            {
                "C": self.cm_C,
                "c": self.cm_c,
                "delta_eps": delta_eps,
                "cycles_this_step": cycles,
            },
            dt,
            rng,
        )

    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        field = self._temp_field(drivers)
        return self.emit_metrics_from_field(state, drivers, field)

    def emit_metrics_from_field(
        self,
        state: ComponentState,
        drivers: Drivers,
        field: np.ndarray,
    ) -> Dict[str, float]:
        # drift_pct grows with health loss and ambient deviation; bounded [0, 1].
        drift = max(0.0, min(1.0, (1.0 - state.health) * 0.5 + abs(drivers.temp_C - 25.0) / 200.0))
        return {
            "predicted_temp_field_x0_C": float(field[0]),
            "predicted_temp_field_xmid_C": float(field[1]),
            "predicted_temp_field_xL_C": float(field[2]),
            "drift_pct": float(drift),
        }


__all__ = ["HeatingElement"]
