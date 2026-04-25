"""Commit-gate tests for the Step 0 mock — PLAN-A §4.2.

Asserts exactly the four conditions §4.2 ships with:
    1. `step` is bit-deterministic for a fixed seed.
    2. All 6 components are reachable from `initial_state`.
    3. `forecast` returns 6 Forecast rows for any horizon_min in 1..60.
    4. `forecast` rejects horizon_min > 60 with ValueError (ADR-015 cap).
"""

from __future__ import annotations

import pytest

from engine import api
from engine.contracts import ComponentId, Drivers, Forecast


def _drivers(hours: float = 0.0, *, seed: int = 42) -> Drivers:
    return Drivers(
        temp_C=25.0,
        humidity=0.6,
        pm25=12.0,
        psd_d50=22.0,
        voltage_stability=0.95,
        cycles=int(hours * 100),
        hours=hours,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="day",
        rng_seed=seed,
    )


def test_step_is_bit_deterministic_for_fixed_seed():
    s0_a = api.initial_state(scenario="stressed", seed=42)
    s0_b = api.initial_state(scenario="stressed", seed=42)
    drivers = _drivers(hours=3.0)

    s1_a = api.step(s0_a, drivers, dt=1.0)
    s1_b = api.step(s0_b, drivers, dt=1.0)

    assert s1_a == s1_b
    assert s1_a.model_dump_json() == s1_b.model_dump_json()


def test_initial_state_has_all_six_components():
    state = api.initial_state(seed=0)
    assert set(state.components.keys()) == set(ComponentId)


@pytest.mark.parametrize("horizon", [1, 10, 30, 59, 60])
def test_forecast_returns_six_rows_for_valid_horizons(horizon: int):
    state = api.initial_state(seed=7)
    state = api.step(state, _drivers(hours=2.0), dt=1.0)

    forecasts = api.forecast(state, horizon_min=horizon)

    assert len(forecasts) == 6
    assert {f.component_id for f in forecasts} == set(ComponentId)
    assert all(isinstance(f, Forecast) and f.horizon_min == horizon for f in forecasts)


@pytest.mark.parametrize("horizon", [61, 120, 999])
def test_forecast_rejects_horizon_above_sixty(horizon: int):
    state = api.initial_state(seed=0)
    with pytest.raises(ValueError):
        api.forecast(state, horizon_min=horizon)
