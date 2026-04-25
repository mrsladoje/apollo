"""R-2 heater regressor surrogate — PLAN-A §8.7 / ADR-001 §11.5.

Drop-in replacement for `HeaterPINN` with the same `__call__(x, t)`
signature. At A4 training time `engine/pinn/train.py` writes the
sklearn `GradientBoostingRegressor` to `models/heater_regressor.pkl`.
If the pickle is absent (or before A4), the surrogate falls back to
the closed-form analytical solution of the 1-D heat diffusion problem
defined in `engine.pinn.pde`. Either path is deterministic on CPU and
preserves the engine's NFR-1 invariant when the PINN is swapped out.
"""

from __future__ import annotations

import math
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np


L_ROD: float = 0.05
T_AMBIENT_REF: float = 25.0
T_DUTY_REF: float = 200.0
KAPPA: float = 5e-6


_DEFAULT_PKL: Path = Path(__file__).resolve().parents[3] / "models" / "heater_regressor.pkl"


def _analytic_temperature(x: np.ndarray, t: float) -> np.ndarray:
    """Closed-form approximation of 1-D heat diffusion with Dirichlet BCs.

    Steady-state linear profile + first-mode transient relaxation. The PINN
    matches this under nominal driver conditions; we use it both as the
    fallback's pre-training behavior and as the FD reference solver target
    in `engine.pinn.data_gen`.
    """
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    L = L_ROD
    # Linear preheat profile (initial condition / steady state with Dirichlet).
    steady = 1.0 - x_arr / L
    if t <= 0.0:
        return np.clip(steady, 0.0, 1.0)
    # First-mode transient: exp(-kappa * (pi/L)^2 * t) decay around steady state.
    decay = math.exp(-KAPPA * (math.pi / L) ** 2 * float(t))
    perturb = (1.0 - steady) * (1.0 - decay) * 0.05
    return np.clip(steady - perturb, 0.0, 1.0)


class HeaterRegressor:
    """sklearn GradientBoostingRegressor surrogate (R-2 fallback)."""

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        t_ambient: float = T_AMBIENT_REF,
        t_duty: float = T_DUTY_REF,
    ) -> None:
        self.t_ambient = float(t_ambient)
        self.t_duty = float(t_duty)
        path = weights_path if weights_path is not None else _DEFAULT_PKL
        self._gbr = None
        if path.exists():
            with open(path, "rb") as fh:
                self._gbr = pickle.load(fh)

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
        if self._gbr is not None:
            t_col = np.full_like(x_arr, float(t), dtype=np.float64)
            features = np.column_stack([x_arr, t_col])
            T_norm = self._gbr.predict(features)
            T_norm = np.clip(T_norm, 0.0, 1.0)
        else:
            T_norm = _analytic_temperature(x_arr, t)
        return self.t_ambient + (self.t_duty - self.t_ambient) * T_norm


__all__ = ["HeaterRegressor", "_analytic_temperature"]
