"""PDE residual on a 100-point validation grid < 1e-3 — PLAN-A §8.8."""

from __future__ import annotations

import numpy as np
import torch

from engine.pinn.inference import HeaterPINN, _DEFAULT_WEIGHTS, _FNN
from engine.pinn.pde import KAPPA, L_ROD, T_MAX_S


def test_pinn_pde_residual_low():
    state = torch.load(_DEFAULT_WEIGHTS, map_location="cpu", weights_only=True)
    net = _FNN()
    net.load_state_dict(state)
    net.train(False)

    rng = np.random.default_rng(0)
    x = rng.uniform(0.0, L_ROD, size=(100, 1)).astype(np.float32)
    t = rng.uniform(0.0, T_MAX_S, size=(100, 1)).astype(np.float32)
    x_t = torch.tensor(x, requires_grad=True)
    t_t = torch.tensor(t, requires_grad=True)
    inp = torch.cat([x_t, t_t], dim=1)
    T = net(inp)
    dT_dx = torch.autograd.grad(
        T, x_t, grad_outputs=torch.ones_like(T), create_graph=True
    )[0]
    d2T_dx2 = torch.autograd.grad(
        dT_dx, x_t, grad_outputs=torch.ones_like(dT_dx), create_graph=True
    )[0]
    dT_dt = torch.autograd.grad(
        T, t_t, grad_outputs=torch.ones_like(T), create_graph=True
    )[0]
    res = dT_dt - KAPPA * d2T_dx2
    msr = float(torch.mean(res * res))
    assert msr < 1e-3, f"mean squared PDE residual {msr:.3e} >= 1e-3 budget"
