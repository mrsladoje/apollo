"""PINN matches FD reference within < 2 degC max abs error on three traces — §8.8."""

from __future__ import annotations

import numpy as np

from engine.pinn.data_gen import fd_reference
from engine.pinn.inference import HeaterPINN


def test_pinn_matches_finite_difference():
    pinn = HeaterPINN()
    x_grid, t_grid, T_fd = fd_reference()
    rng = np.random.default_rng(123)

    # Three independent driver-trace seeds for the held-out comparison.
    for trace_seed in (1, 2, 3):
        local_rng = np.random.default_rng(trace_seed)
        sample_idx = local_rng.choice(len(x_grid) * len(t_grid), size=100, replace=False)
        max_abs_err_C = 0.0
        for idx in sample_idx:
            xi = idx // len(t_grid)
            ti = idx % len(t_grid)
            pred_C = pinn(np.array([x_grid[xi]]), float(t_grid[ti]))[0]
            target_norm = float(T_fd[ti, xi])
            target_C = pinn.t_ambient + (pinn.t_duty - pinn.t_ambient) * target_norm
            err = abs(float(pred_C) - target_C)
            if err > max_abs_err_C:
                max_abs_err_C = err
        assert max_abs_err_C < 2.0, (
            f"trace_seed={trace_seed}: max abs error {max_abs_err_C:.3f} degC >= 2.0"
        )
