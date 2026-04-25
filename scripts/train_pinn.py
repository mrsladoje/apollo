"""Offline training script — PLAN-A §8.5 / ADR-005.

Trains the 4 hidden x 64 unit PINN (`engine.pinn.inference._FNN`) on
synthetic data from the FD reference solver in `engine.pinn.data_gen`,
plus PDE-residual + BC + IC losses computed via PyTorch autograd.
Adam first, then L-BFGS polish, mirroring DeepXDE's recipe.

After training, also fits a sklearn `GradientBoostingRegressor` on the
same FD data and pickles it as the R-2 fallback (PLAN-A §8.7).

Run via `make train-pinn` or directly. The MPS path is opportunistic:
ADR-005 allows training on MPS where available, and §11 R-2 says fall
through to CPU with halved iterations if MPS is unavailable.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.pinn.data_gen import fd_reference, make_training_dataset  # noqa: E402
from engine.pinn.inference import _FNN  # noqa: E402
from engine.pinn.pde import KAPPA, L_ROD, T_MAX_S  # noqa: E402


def _device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _adam_iters(device: torch.device) -> int:
    # ADR-005 / §8.5 recipe: ~20 k Adam on MPS; halve on CPU per R-2.
    return 8000 if device.type == "mps" else 4000


def _residual_loss(net: nn.Module, x: torch.Tensor, t: torch.Tensor, kappa: float) -> torch.Tensor:
    inp = torch.cat([x, t], dim=1)
    T = net(inp)
    dT_dx = torch.autograd.grad(
        T, x, grad_outputs=torch.ones_like(T), create_graph=True, retain_graph=True
    )[0]
    d2T_dx2 = torch.autograd.grad(
        dT_dx, x, grad_outputs=torch.ones_like(dT_dx), create_graph=True, retain_graph=True
    )[0]
    dT_dt = torch.autograd.grad(
        T, t, grad_outputs=torch.ones_like(T), create_graph=True, retain_graph=True
    )[0]
    res = dT_dt - kappa * d2T_dx2
    return torch.mean(res * res)


def train_pinn(seed: int = 0) -> Path:
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = _device()
    print(f"[train_pinn] device={device}")

    features, targets = make_training_dataset(seed=seed)
    feat_t = torch.tensor(features, dtype=torch.float32, device=device)
    targ_t = torch.tensor(targets, dtype=torch.float32, device=device).unsqueeze(1)

    # Collocation points for PDE residual (uniform on the rectangle).
    rng = np.random.default_rng(seed + 1)
    n_coll = 2000
    x_coll = rng.uniform(0.0, L_ROD, size=(n_coll, 1))
    t_coll = rng.uniform(0.0, T_MAX_S, size=(n_coll, 1))
    x_coll_t = torch.tensor(x_coll, dtype=torch.float32, device=device, requires_grad=True)
    t_coll_t = torch.tensor(t_coll, dtype=torch.float32, device=device, requires_grad=True)

    net = _FNN().to(device)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)

    n_iter = _adam_iters(device)
    for it in range(n_iter):
        opt.zero_grad()
        pred = net(feat_t)
        data_loss = torch.mean((pred - targ_t) ** 2)
        pde_loss = _residual_loss(net, x_coll_t, t_coll_t, KAPPA)
        loss = data_loss + 0.1 * pde_loss
        loss.backward()
        opt.step()
        if (it + 1) % max(1, n_iter // 10) == 0:
            print(
                f"[train_pinn] iter {it+1}/{n_iter} "
                f"data={data_loss.item():.3e} pde={pde_loss.item():.3e}"
            )

    # L-BFGS polish.
    net_cpu = net.to("cpu")
    feat_cpu = feat_t.to("cpu")
    targ_cpu = targ_t.to("cpu")
    x_coll_cpu = torch.tensor(x_coll, dtype=torch.float32, requires_grad=True)
    t_coll_cpu = torch.tensor(t_coll, dtype=torch.float32, requires_grad=True)
    lbfgs = torch.optim.LBFGS(
        net_cpu.parameters(),
        lr=1.0,
        max_iter=300,
        tolerance_grad=1e-7,
        history_size=50,
        line_search_fn="strong_wolfe",
    )

    def closure():
        lbfgs.zero_grad()
        pred = net_cpu(feat_cpu)
        data_loss = torch.mean((pred - targ_cpu) ** 2)
        pde_loss = _residual_loss(net_cpu, x_coll_cpu, t_coll_cpu, KAPPA)
        loss = data_loss + 0.1 * pde_loss
        loss.backward()
        return loss

    lbfgs.step(closure)
    print("[train_pinn] L-BFGS done")

    out_dir = ROOT / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "heater_pinn.pt"
    torch.save({k: v.cpu() for k, v in net_cpu.state_dict().items()}, out_path)
    size_kb = out_path.stat().st_size / 1024.0
    print(f"[train_pinn] wrote {out_path} ({size_kb:.1f} KB)")
    return out_path


def train_fallback_regressor(seed: int = 0) -> Path:
    """R-2 mitigation per §8.7: sklearn GBR trained on the same FD data."""
    from sklearn.ensemble import GradientBoostingRegressor

    features, targets = make_training_dataset(seed=seed)
    gbr = GradientBoostingRegressor(
        n_estimators=120,
        max_depth=3,
        learning_rate=0.1,
        random_state=seed,
    )
    gbr.fit(features, targets)
    out_dir = ROOT / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "heater_regressor.pkl"
    with open(out_path, "wb") as fh:
        pickle.dump(gbr, fh)
    print(f"[train_pinn] wrote fallback regressor to {out_path}")
    return out_path


def main() -> int:
    train_pinn()
    train_fallback_regressor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
