"""Recoater Blade — PLAN-A §6.3 row 1, ADR-006 (Archard + Weibull impact).

Composition: Archard exponential height loss + impact-event Weibull layered.
Drivers: psd_d50, pm25, cycles. Metrics: blade_thickness_mm, impact_count.

Parameter anchors (ADR-006 table):
- Archard k = 1e-6 (range 1e-7..1e-5 ceramic-on-metal abrasive contact;
  Aghababaei/Warner/Molinari, Nat. Commun. 7, 11816, 2016).
- Weibull beta = 2.0 (wear-out, Pfeiffer 2021 oxide ceramic AM).
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from engine.components.base import Component
from engine.contracts import ComponentId, ComponentState, Drivers
from engine.failure_models import ExponentialDecay, WeibullDecay


class RecoaterBlade(Component):
    component_id = ComponentId.BLADE
    intrinsic_alpha: float = 1e-6  # Archard wear coefficient (ADR-006)

    # PSD/PM2.5 stress scale: chosen so a Stressed-scenario 600-min run
    # leaves the blade in DEGRADED (~ 0.5 health) without coupling, per
    # PLAN-A §4.1 mock targets. R-1 mitigation: only the magnitude is
    # tunable; the structure (psd / pm25 multiplicative) reflects the
    # ADR-006 abrasion-+-contamination phenomenology.
    stress_scale: float = 800.0

    # Impact-event Weibull layered on top of exponential height loss.
    beta_impact: float = 2.0
    eta_impact_cycles: float = 5.0e4

    thickness_init_mm: float = 1.0

    def __init__(self) -> None:
        self._exp = ExponentialDecay()
        self._weib = WeibullDecay()

    def _stress(self, drivers: Drivers) -> float:
        psd_factor = max(drivers.psd_d50, 1e-6) / 20.0
        pm_factor = 1.0 + drivers.pm25 / 50.0
        return psd_factor * pm_factor * self.stress_scale

    def intrinsic_decay(
        self,
        state: ComponentState,
        drivers: Drivers,
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        dh_height = self._exp.decay(
            state.health,
            {"alpha": self.intrinsic_alpha, "stress": self._stress(drivers)},
            dt,
            rng,
        )
        t_impact = max(1.0, float(drivers.cycles))
        dh_impact = self._weib.decay(
            state.health,
            {"beta": self.beta_impact, "eta": self.eta_impact_cycles, "t": t_impact},
            dt,
            rng,
        )
        return dh_height + dh_impact

    def emit_metrics(
        self,
        state: ComponentState,
        drivers: Drivers,
    ) -> Dict[str, float]:
        return {
            "blade_thickness_mm": float(self.thickness_init_mm * state.health),
            "impact_count": float(int(drivers.cycles * (1.0 - state.health))),
        }


__all__ = ["RecoaterBlade"]
