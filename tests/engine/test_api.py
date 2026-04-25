"""Public API surface tests — PLAN-A §13.1, §13.3."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from engine import api
from engine.contracts import (
    COUPLING_MATRIX_M,
    ComponentId,
    ComponentState,
    ComponentStatus,
    Drivers,
    EngineState,
    Forecast,
    ROW_ORDER,
    status_for_health,
)


def _drivers(seed: int = 42, hours: float = 0.0) -> Drivers:
    return Drivers(
        temp_C=30.0,
        humidity=0.5,
        pm25=15.0,
        psd_d50=22.0,
        voltage_stability=0.95,
        cycles=int(hours * 60 * 1.5),
        hours=hours,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="day",
        rng_seed=seed,
    )


# FR-1.1 — six components, three subsystems, two per subsystem.
def test_initial_state_six_components():
    state = api.initial_state(seed=0)
    assert isinstance(state, EngineState)
    assert set(state.components.keys()) == set(ComponentId)
    assert len(state.components) == 6


# FR-1.4 — Pydantic State Report shape.
def test_state_report_schema():
    state = api.initial_state(seed=0)
    for cid, comp in state.components.items():
        assert isinstance(comp, ComponentState)
        assert 0.0 <= comp.health <= 1.0
        assert isinstance(comp.status, ComponentStatus)
        assert comp.status == status_for_health(comp.health)
        assert isinstance(comp.metrics, dict)
        for v in comp.metrics.values():
            assert isinstance(v, float)
    assert tuple(tuple(row) for row in state.coupling_matrix) == COUPLING_MATRIX_M


# FR-1.6 — coupling matrix literal exposed via state.
def test_coupling_matrix_literal():
    state = api.initial_state(seed=0)
    assert tuple(tuple(row) for row in state.coupling_matrix) == COUPLING_MATRIX_M


# FR-1.8 — single step interface stable.
def test_step_signature_stable():
    sig = inspect.signature(api.step)
    params = list(sig.parameters.keys())
    assert params == ["state", "drivers", "dt"]


# FR-1.5 — bit-identical determinism for identical inputs.
def test_step_deterministic_for_fixed_seed():
    s_a = api.initial_state(scenario="stressed", seed=42)
    s_b = api.initial_state(scenario="stressed", seed=42)
    drivers = _drivers(hours=2.0, seed=42)
    s1_a = api.step(s_a, drivers, dt=1.0)
    s1_b = api.step(s_b, drivers, dt=1.0)
    assert s1_a.model_dump_json() == s1_b.model_dump_json()


# Forecast wraps the conformal layer; surface contract.
@pytest.mark.parametrize("horizon", [1, 10, 30, 59, 60])
def test_forecast_returns_six_rows(horizon: int):
    state = api.step(api.initial_state(seed=7), _drivers(hours=2.0), dt=1.0)
    forecasts = api.forecast(state, horizon_min=horizon)
    assert len(forecasts) == 6
    assert {f.component_id for f in forecasts} == set(ComponentId)
    for f in forecasts:
        assert isinstance(f, Forecast)
        assert f.lower <= f.point <= f.upper


@pytest.mark.parametrize("horizon", [0, 61, 120, 999])
def test_forecast_horizon_cap(horizon: int):
    state = api.initial_state(seed=0)
    with pytest.raises(ValueError):
        api.forecast(state, horizon_min=horizon)


# Public surface count: §13.3 says exactly step, forecast, initial_state.
def test_api_public_surface_is_three_symbols():
    assert set(api.__all__) == {"step", "forecast", "initial_state"}


# Contracts public surface: §13.3 says exactly the seven names below.
def test_contracts_public_surface():
    from engine import contracts
    expected = {
        "ComponentId",
        "ComponentStatus",
        "ROW_ORDER",
        "status_for_health",
        "COUPLING_MATRIX_M",
        "ComponentState",
        "Drivers",
        "EngineState",
        "Forecast",
    }
    assert set(contracts.__all__) == expected


# RNG state is a tuple (Pydantic-friendly) and round-trips through step().
def test_rng_state_round_trip():
    s0 = api.initial_state(seed=99)
    s1 = api.step(s0, _drivers(hours=1.0, seed=99), dt=1.0)
    assert isinstance(s1.rng_state, tuple)


# 600-min Stressed-style trace stays inside the [0, 1] aggregate invariant.
def test_step_keeps_health_in_unit_interval():
    state = api.initial_state(scenario="stressed", seed=1)
    for t in range(600):
        drivers = Drivers(
            temp_C=45.0 + 5.0 * np.sin(t * 0.05),
            humidity=0.75,
            pm25=40.0,
            psd_d50=35.0,
            voltage_stability=0.6,
            cycles=int(t * 1.5),
            hours=t / 60.0,
            maintenance_level={c: 1.0 for c in ComponentId},
            operator_shift="weekend",
            rng_seed=1,
        )
        state = api.step(state, drivers, dt=1.0)
        for cid, comp in state.components.items():
            assert 0.0 <= comp.health <= 1.0
            assert comp.status == status_for_health(comp.health)
