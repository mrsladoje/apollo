"""Coffin-Manson thermal-fatigue — PLAN-A §5.3 / ADR-006.

`N_f = C * (delta_eps_p)^(-c)`; per-step decrement `dH = -cycles_this_step / N_f`.
Used by Thermal Firing Resistors (c=2.0, IS&T Print4Fab 2020 thin-film range
1.9-2.5) and the Heating Element layered on top of the PINN's predicted
temperature swing (CSC-B).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from engine.failure_models.base import FailureModel


class CoffinManson(FailureModel):
    def decay(
        self,
        health: float,
        drivers: Mapping[str, float],
        dt: float,
        rng: np.random.Generator,
    ) -> float:
        cycles = float(drivers["cycles_this_step"])
        if cycles == 0.0:
            return 0.0
        delta_eps = float(drivers["delta_eps"])
        if delta_eps <= 0.0:
            return 0.0
        c_const = float(drivers["C"])
        c_exp = float(drivers["c"])
        n_f = c_const * (delta_eps ** (-c_exp))
        return -cycles / n_f


__all__ = ["CoffinManson"]
