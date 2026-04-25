"""Synthetic training-data generator for the heater PINN — PLAN-A §8.4.

Finite-difference reference solver for `dT/dt = kappa * d^2 T/dx^2` on
the geometry defined in `engine.pinn.pde`. The PINN learns the same PDE,
so the training data acts as a consistency check rather than a
generalization benchmark (per ADR-005 §"Negative tradeoffs").
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from engine.pinn.pde import KAPPA, L_ROD, T_MAX_S


def fd_reference(
    nx: int = 41,
    nt: int = 601,
    *,
    kappa: float = KAPPA,
    L: float = L_ROD,
    T_max: float = T_MAX_S,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forward-Euler FD for the normalized heat-diffusion problem.

    Boundary T(0, t) = 1.0, T(L, t) = 0.0; initial T(x, 0) = 1 - x/L.
    Returns `(x_grid, t_grid, T)` where `T.shape == (nt, nx)`.
    Stable when `kappa * dt / dx^2 < 0.5`.
    """
    x = np.linspace(0.0, L, nx)
    t = np.linspace(0.0, T_max, nt)
    dx = x[1] - x[0]
    dt = t[1] - t[0]
    r = kappa * dt / (dx * dx)
    assert r < 0.5, f"FD instability: r={r:.3f} >= 0.5"

    T = np.zeros((nt, nx), dtype=np.float64)
    T[0, :] = 1.0 - x / L
    T[:, 0] = 1.0
    T[:, -1] = 0.0
    for n in range(nt - 1):
        T[n + 1, 1:-1] = T[n, 1:-1] + r * (T[n, 2:] - 2.0 * T[n, 1:-1] + T[n, :-2])
        T[n + 1, 0] = 1.0
        T[n + 1, -1] = 0.0
    return x, t, T


def make_training_dataset(seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """5000 collocation points + 500 boundary + 500 IC, per §8.4.

    Returns `(features, targets)` arrays where features is `(N, 2)` of
    `(x, t)` pairs and targets is `(N,)` of normalized temperatures.
    """
    x_grid, t_grid, T = fd_reference()
    rng = np.random.default_rng(seed)

    nx, nt = x_grid.size, t_grid.size

    # 5000 interior collocation points sampled uniformly from the (x, t) field.
    n_int = 5000
    xi = rng.integers(1, nx - 1, size=n_int)
    ti = rng.integers(1, nt - 1, size=n_int)
    interior = np.column_stack([x_grid[xi], t_grid[ti]])
    interior_T = T[ti, xi]

    # 500 boundary samples (250 each face).
    n_bc = 250
    t_left = rng.choice(nt, size=n_bc)
    t_right = rng.choice(nt, size=n_bc)
    bc_left = np.column_stack([np.full(n_bc, x_grid[0]), t_grid[t_left]])
    bc_right = np.column_stack([np.full(n_bc, x_grid[-1]), t_grid[t_right]])
    bc_T = np.concatenate(
        [np.ones(n_bc, dtype=np.float64), np.zeros(n_bc, dtype=np.float64)]
    )
    bc = np.vstack([bc_left, bc_right])

    # 500 IC samples.
    n_ic = 500
    xi0 = rng.choice(nx, size=n_ic)
    ic = np.column_stack([x_grid[xi0], np.zeros(n_ic, dtype=np.float64)])
    ic_T = T[0, xi0]

    features = np.vstack([interior, bc, ic]).astype(np.float64)
    targets = np.concatenate([interior_T, bc_T, ic_T]).astype(np.float64)
    return features, targets


def write_training_dataset(out_dir: Path, *, seed: int = 0) -> Path:
    """Persist (features, targets) under data/pinn_training/ for reproducibility."""
    out_dir.mkdir(parents=True, exist_ok=True)
    features, targets = make_training_dataset(seed=seed)
    path = out_dir / "training_set.npz"
    np.savez(path, features=features, targets=targets)
    return path


__all__ = ["fd_reference", "make_training_dataset", "write_training_dataset"]
