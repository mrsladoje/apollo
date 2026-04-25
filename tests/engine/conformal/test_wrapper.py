"""Conformal wrapper surface tests — PLAN-A §9.5."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.api import forecast, initial_state, step
from engine.contracts import ComponentId, Drivers, Forecast, ROW_ORDER
from engine.conformal.wrapper import ConformalForecaster


_DATA = Path(__file__).resolve().parents[3] / "data" / "conformal_residuals"


def _drivers(hours: float = 0.5) -> Drivers:
    return Drivers(
        temp_C=30.0,
        humidity=0.5,
        pm25=15.0,
        psd_d50=22.0,
        voltage_stability=0.9,
        cycles=10,
        hours=hours,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="day",
        rng_seed=11,
    )


def test_conformal_returns_triple():
    state = step(initial_state(seed=11), _drivers(), dt=1.0)
    for h in (1, 5, 30, 60):
        rows = forecast(state, horizon_min=h)
        assert len(rows) == 6
        for f in rows:
            assert isinstance(f, Forecast)
            assert f.horizon_min == h
            assert f.lower <= f.point <= f.upper


@pytest.mark.parametrize("bad", [0, 61, 120, 999])
def test_conformal_horizon_cap(bad: int):
    state = initial_state(seed=0)
    with pytest.raises(ValueError):
        forecast(state, horizon_min=bad)


def test_conformal_band_widens_with_horizon():
    state = step(initial_state(seed=12), _drivers(), dt=1.0)
    for cid in ROW_ORDER:
        h = state.components[cid].health
        f10 = ConformalForecaster(cid).predict(h, horizon_min=10)
        f60 = ConformalForecaster(cid).predict(h, horizon_min=60)
        assert (f60.upper - f60.lower) > (f10.upper - f10.lower), (
            f"band must widen with horizon for {cid.value}"
        )


def test_conformal_residuals_persisted():
    """data/conformal_residuals/<component>.npz exists for every component."""
    for cid in ComponentId:
        assert (_DATA / f"{cid.value}.npz").exists(), (
            f"missing residual file for {cid.value}; "
            "run `python3 -c 'from engine.conformal import calibrate_all; calibrate_all()'`."
        )
