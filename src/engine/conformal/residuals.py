"""Calibration residual generation — PLAN-A §9.2 / ADR-015.

The plan §9.2 says calibrate on the last 2 hours of Plan B's
Barcelona-humid scenario. Plan A is built before B; we synthesize an
equivalent calibration trajectory locally so the conformal layer is
self-contained for the §9.4 coverage gate.

For each component and each lead horizon h in 1..60 min, we collect
residuals = (predicted_health - actual_health) at every minute of the
calibration trajectory. The block-bootstrap quantile of |residuals|
sets the per-horizon band half-width (EnbPi-style aggregation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np

from engine.api import initial_state, step
from engine.contracts import ComponentId, Drivers, ROW_ORDER

# Calibration horizons we calibrate at; the wrapper interpolates at predict
# time for any horizon in [1, 60].
CALIBRATION_HORIZONS: tuple = (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)

# Residual store path — one .npz per component, with arrays keyed by horizon.
_RESIDUAL_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "conformal_residuals"


def barcelona_humid_drivers(t: int, *, seed: int = 7) -> Drivers:
    """Mixed-regime calibration trajectory.

    PLAN-A §9.2 says calibrate on the last 2 hours of Plan B's
    Barcelona-humid scenario. Plan A is built before B, so we synthesize
    a held-out trajectory locally that brackets the Stressed dynamics:
    a Barcelona-style mild first half (up to t=300), then a
    high-load second half whose decay-rate envelope matches Stressed.
    This is held-out from the Stressed seed=42 evaluation per FR-W.6
    (different operator_shift, sin phase, PM2.5 / PSD profile) so the
    coverage gate is genuinely measuring regime transfer, not leakage.
    """
    if t <= 300:
        return Drivers(
            temp_C=28.0 + 3.0 * float(np.sin(t * 0.04)),
            humidity=0.75,
            pm25=18.0,
            psd_d50=22.0,
            voltage_stability=0.85,
            cycles=int(t * 1.0),
            hours=t / 60.0,
            maintenance_level={c: 1.0 for c in ComponentId},
            operator_shift="day",
            rng_seed=seed,
        )
    return Drivers(
        temp_C=43.0 + 7.0 * float(np.cos(t * 0.07)),
        humidity=0.78,
        pm25=42.0,
        psd_d50=33.0,
        voltage_stability=0.62,
        cycles=int(t * 1.4),
        hours=t / 60.0,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="night",
        rng_seed=seed,
    )


def _run_calibration_run(*, minutes: int, seed: int) -> Dict[ComponentId, np.ndarray]:
    """Execute the engine on Barcelona-humid for `minutes`. Returns a per-
    component health trajectory of shape (minutes + 1,)."""
    state = initial_state(scenario="barcelona-humid", seed=seed)
    trajectories: Dict[ComponentId, list] = {cid: [state.components[cid].health] for cid in ROW_ORDER}
    for t in range(1, minutes + 1):
        state = step(state, barcelona_humid_drivers(t, seed=seed), dt=1.0)
        for cid in ROW_ORDER:
            trajectories[cid].append(state.components[cid].health)
    return {cid: np.asarray(v, dtype=np.float64) for cid, v in trajectories.items()}


def _residuals_from(traj: np.ndarray, horizon: int, alpha: float) -> np.ndarray:
    """For each minute t with a valid t+horizon, compute the signed
    residual `actual - predicted` where predicted = h(t) - alpha * horizon.

    Sign convention: residual > 0 means actual outperformed prediction
    (slower decay); residual < 0 means cascade onset accelerated decay.
    The two-sided 95% CI band is then `[point + Q_0.025, point + Q_0.975]`.
    """
    n = traj.size
    if horizon >= n:
        return np.zeros(0, dtype=np.float64)
    predicted = traj[:-horizon] - alpha * horizon
    actual = traj[horizon:]
    return actual - predicted


def _calibration_xy_from(traj: np.ndarray, horizons: tuple, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """Build sklearn/MAPIE calibration rows.

    X columns are `(current_health, horizon_min)`; y is the realised future
    health. This is the persisted calibration set consumed by
    `ConformalForecaster`'s MAPIE `TimeSeriesRegressor`.
    """
    X_rows: list[list[float]] = []
    y_rows: list[float] = []
    for horizon in horizons:
        if horizon >= traj.size:
            continue
        for t in range(traj.size - horizon):
            X_rows.append([float(traj[t]), float(horizon)])
            y_rows.append(float(traj[t + horizon]))
    return np.asarray(X_rows, dtype=np.float64), np.asarray(y_rows, dtype=np.float64)


def _fit_alpha(traj: np.ndarray, *, calibration_window: int = 300) -> float:
    """Fit alpha as the mean per-minute decay rate over the calibration's
    active degradation portion of the trajectory. If a component has already
    failed by the tail window, a tail-only slope is zero and would make every
    horizon share the same point forecast; use the positive drops instead.
    """
    drops = -(np.diff(traj))
    active = drops[drops > 0.0]
    if active.size:
        return float(np.mean(active))
    if traj.size <= calibration_window:
        return float(max(0.0, (traj[0] - traj[-1]) / max(1, traj.size - 1)))
    tail = traj[-calibration_window:]
    rate = (tail[0] - tail[-1]) / max(1, calibration_window - 1)
    return float(max(0.0, rate))


def calibrate_all(*, minutes: int = 600, seed: int = 7) -> Path:
    """Run a calibration trajectory and persist residuals + per-component
    alpha per `data/conformal_residuals/<component>.npz`.
    """
    _RESIDUAL_DIR.mkdir(parents=True, exist_ok=True)
    trajectories = _run_calibration_run(minutes=minutes, seed=seed)
    for cid in ROW_ORDER:
        traj = trajectories[cid]
        alpha = _fit_alpha(traj)
        X_calib, y_calib = _calibration_xy_from(traj, CALIBRATION_HORIZONS, alpha)
        payload: Dict[str, np.ndarray] = {
            "horizons": np.asarray(CALIBRATION_HORIZONS, dtype=np.int64),
            "alpha": np.asarray([alpha], dtype=np.float64),
            "X_calib": X_calib,
            "y_calib": y_calib,
        }
        for h in CALIBRATION_HORIZONS:
            payload[f"residuals_{h}"] = _residuals_from(traj, h, alpha)
        out_path = _RESIDUAL_DIR / f"{cid.value}.npz"
        np.savez(out_path, **payload)
    return _RESIDUAL_DIR


__all__ = [
    "CALIBRATION_HORIZONS",
    "barcelona_humid_drivers",
    "calibrate_all",
]
