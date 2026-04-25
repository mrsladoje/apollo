"""Offline training script — PLAN-A §8.5 / ADR-005.

Trains the 4 hidden x 64 unit PINN with DeepXDE's `TimePDE` setup in
`engine.pinn.train`, then fits the sklearn fallback regressor on the same
finite-difference data.

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.pinn.data_gen import make_training_dataset  # noqa: E402
from engine.pinn.train import train_pinn as train_deepxde_pinn  # noqa: E402


def train_pinn(seed: int = 0) -> Path:
    out_path = train_deepxde_pinn(seed=seed)
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
