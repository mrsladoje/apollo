"""Weibull hazard — PLAN-A §5.3 / ADR-006.

Instantaneous hazard `h(t) = (beta/eta) * (t/eta)^(beta-1)`; per-step decrement
`dH = -h(t) * dt`. beta > 1 (wear-out region) for all consumers per ADR-006.
Used by Drive Motor (beta=1.5, eta=2000h, ISO 281), Nozzle Plate
(beta=2.5, IS&T Print4Fab 2020), Recoater Blade impact-event Weibull (beta=2.0).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from engine.failure_models.base import FailureModel


class WeibullDecay(FailureModel):
    def decay(
        self,
        health: float,
        drivers: Mapping[str, float],
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        beta = float(drivers["beta"])
        eta = float(drivers["eta"])
        t = float(drivers["t"])
        if t <= 0.0 or eta <= 0.0:
            return 0.0
        # h(t) = (beta/eta) * (t/eta)^(beta-1) — closed-form Weibull hazard.
        hazard = (beta / eta) * (t / eta) ** (beta - 1.0)
        return -hazard * dt


__all__ = ["WeibullDecay"]
