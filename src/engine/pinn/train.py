"""DeepXDE training entrypoint for the heater PINN — PLAN-A §8.5 / ADR-005.

This module owns the actual DeepXDE `TimePDE` setup. It writes the frozen
weights in the key layout expected by `engine.pinn.inference._FNN`, so runtime
inference stays a small PyTorch-only dependency path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch

from engine.pinn.data_gen import make_training_dataset, write_training_dataset
from engine.pinn.pde import KAPPA, L_ROD, T_MAX_S


def _device_name() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def _translated_state_dict(state: dict) -> dict:
    """Convert DeepXDE's `linears.*` keys to our inference `_FNN` keys."""
    translated = {}
    for key, value in state.items():
        if key.startswith("linears."):
            key = key.replace("linears.", "layers.", 1)
        translated[key] = value.detach().cpu()
    return translated


def train_pinn(
    *,
    weights_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    seed: int = 0,
    adam_iterations: int = 20_000,
    lbfgs: bool = True,
) -> Path:
    """Train and freeze the 4x64 DeepXDE heat-diffusion PINN.

    The default settings match PLAN-A §8.5. Callers can lower
    `adam_iterations` for local smoke tests.
    """
    import deepxde as dde

    np.random.seed(seed)
    torch.manual_seed(seed)
    dde.config.set_default_float("float32")

    root = Path(__file__).resolve().parents[3]
    out_path = weights_path or root / "models" / "heater_pinn.pt"
    training_dir = data_dir or root / "data" / "pinn_training"
    write_training_dataset(training_dir, seed=seed)
    features, targets = make_training_dataset(seed=seed)

    if _device_name() == "mps":
        torch.set_default_device("mps")

    geom = dde.geometry.Interval(0.0, L_ROD)
    timedomain = dde.geometry.TimeDomain(0.0, T_MAX_S)
    geomtime = dde.geometry.GeometryXTime(geom, timedomain)

    def pde_residual(x, T):
        dT_dt = dde.grad.jacobian(T, x, j=1)
        d2T_dx2 = dde.grad.hessian(T, x, j=0)
        return dT_dt - KAPPA * d2T_dx2

    def left_boundary(x, on_boundary):
        return on_boundary and np.isclose(x[0], 0.0)

    def right_boundary(x, on_boundary):
        return on_boundary and np.isclose(x[0], L_ROD)

    bc_inner = dde.icbc.DirichletBC(geomtime, lambda x: 1.0, left_boundary)
    bc_outer = dde.icbc.DirichletBC(geomtime, lambda x: 0.0, right_boundary)
    ic = dde.icbc.IC(
        geomtime,
        lambda x: 1.0 - x[:, 0:1] / L_ROD,
        lambda _, on_initial: on_initial,
    )
    data_anchor = dde.icbc.PointSetBC(
        features.astype(np.float32),
        targets.reshape(-1, 1).astype(np.float32),
    )

    data = dde.data.TimePDE(
        geomtime,
        pde_residual,
        [bc_inner, bc_outer, ic, data_anchor],
        num_domain=5000,
        num_boundary=500,
        num_initial=500,
    )
    net = dde.nn.FNN([2, 64, 64, 64, 64, 1], "tanh", "Glorot uniform")
    model = dde.Model(data, net)
    model.compile("adam", lr=1e-3, loss_weights=[1, 1, 1, 1, 10])
    model.train(iterations=adam_iterations)
    if lbfgs:
        model.compile("L-BFGS")
        model.train()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_translated_state_dict(model.net.state_dict()), out_path)
    torch.set_default_device("cpu")
    return out_path


__all__ = ["train_pinn"]
