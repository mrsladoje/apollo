"""Frozen-weights heater PINN inference — PLAN-A §8.6 / ADR-005.

Holds an FNN with the §8.3 architecture (4 hidden x 64 units, tanh) and
loads `models/heater_pinn.pt` if present. If the artifact is absent
(pre-training) or `APOLLO_PINN_FALLBACK=1` is set, the R-2 sklearn
fallback (`engine.pinn.fallback`) is wired in transparently — same
`__call__(x, t)` signature, < 5 ms target on CPU per NFR-3.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

# 1-D heater rod geometry — must match training (engine/pinn/pde.py).
L_ROD: float = 0.05            # 5 cm rod
T_AMBIENT_REF: float = 25.0    # degC reference for the surrogate's interior call
T_DUTY_REF: float = 200.0      # degC nominal heater hot-side temperature
KAPPA: float = 5e-6            # m^2/s, NiCr-class refractory diffusivity (ADR-006)


_DEFAULT_WEIGHTS: Path = Path(__file__).resolve().parents[3] / "models" / "heater_pinn.pt"


class _FNN(nn.Module):
    """4 hidden x 64 units, tanh — §8.3 architecture."""

    def __init__(self) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        widths = [2, 64, 64, 64, 64, 1]
        for a, b in zip(widths[:-1], widths[1:]):
            layers.append(nn.Linear(a, b))
        self.layers = nn.ModuleList(layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = x
        for i, layer in enumerate(self.layers):
            h = layer(h)
            if i < len(self.layers) - 1:
                h = torch.tanh(h)
        return h


class HeaterPINN:
    """CPU inference wrapper. Deterministic for fixed weights (NFR-1, NFR-3).

    `__call__(x, t)` returns predicted T(x, t) in degC for the given x array
    and scalar time t (in seconds since the heater started its current duty
    pulse). Weights are loaded once at construction; subsequent calls are
    pure feed-forward and respect `torch.inference_mode()`.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        t_ambient: float = T_AMBIENT_REF,
        t_duty: float = T_DUTY_REF,
    ) -> None:
        self.t_ambient = float(t_ambient)
        self.t_duty = float(t_duty)
        self._fallback = None
        self._net: Optional[_FNN] = None

        if os.environ.get("APOLLO_PINN_FALLBACK") == "1":
            from engine.pinn.fallback import HeaterRegressor
            self._fallback = HeaterRegressor()
            return

        path = weights_path if weights_path is not None else _DEFAULT_WEIGHTS
        if path.exists():
            self._net = _FNN()
            state = torch.load(path, map_location="cpu", weights_only=True)
            self._net.load_state_dict(state)
            self._net.eval()
            for p in self._net.parameters():
                p.requires_grad_(False)
        else:
            # No artifact yet — degrade gracefully to the R-2 surrogate so
            # downstream components still get a deterministic temp field.
            from engine.pinn.fallback import HeaterRegressor
            self._fallback = HeaterRegressor()

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        if self._fallback is not None:
            return self._fallback(x, t)
        assert self._net is not None
        x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
        t_col = np.full_like(x_arr, float(t), dtype=np.float64)
        inp = np.column_stack([x_arr, t_col]).astype(np.float32)
        with torch.inference_mode():
            out = self._net(torch.from_numpy(inp))
        # The trained net predicts a normalized temperature in [0, 1]; rescale.
        T = out.cpu().numpy().reshape(-1)
        return self.t_ambient + (self.t_duty - self.t_ambient) * T


__all__ = ["HeaterPINN", "L_ROD", "T_AMBIENT_REF", "T_DUTY_REF", "KAPPA"]
