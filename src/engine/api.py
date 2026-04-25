"""Public engine surface — PLAN-A §3.2.

Exactly three symbols cross this boundary: `step`, `forecast`,
`initial_state`. Everything else under `engine/` is implementation detail
per ADR-021 (Engine bounded context published language).

`APOLLO_ENGINE=mock` routes to `engine.mock_engine` for Plan B's smoke
tests / demo dry-runs (PLAN-A §4.3). Otherwise the real engine composes
intrinsic decay + the §7 coupling matrix + the §7.3 CSC-B physics and
wraps `forecast()` with the §9 MAPIE conformal layer (loaded lazily so
A1-A3 unit tests can run without sklearn warm-up cost).
"""

from __future__ import annotations

import os
from typing import List

import numpy as np

from engine.cascades import csc_b as _csc_b
from engine.components import build_components
from engine.contracts import (
    COUPLING_MATRIX_M,
    ComponentId,
    ComponentState,
    Drivers,
    EngineState,
    Forecast,
    ROW_ORDER,
    status_for_health,
)
from engine.coupling import apply_coupling
from engine.components.heater import _SAMPLE_X as _HEATER_SAMPLE_X


def _is_mock() -> bool:
    return os.environ.get("APOLLO_ENGINE") == "mock"


# Module-level cache for the component registry. Each component is
# stateless across step() calls (mutable state lives in the EngineState
# aggregate per ADR-021), so caching is safe and avoids re-loading the
# 56 KB PINN weights file on every step. Cache rebuilds when the
# APOLLO_PINN_FALLBACK env var flips so the R-2 path remains testable.
_COMPONENT_CACHE = None
_COMPONENT_CACHE_KEY = None


def _components():
    global _COMPONENT_CACHE, _COMPONENT_CACHE_KEY
    key = os.environ.get("APOLLO_PINN_FALLBACK", "")
    if _COMPONENT_CACHE is None or _COMPONENT_CACHE_KEY != key:
        _COMPONENT_CACHE = build_components()
        _COMPONENT_CACHE_KEY = key
    return _COMPONENT_CACHE


def initial_state(scenario: str = "default", seed: int = 0) -> EngineState:
    """Construct a fresh EngineState with all 6 components at health=1.0
    (PLAN-A §3.2). RNG state is the seeded numpy Generator state tuple
    so two `initial_state(seed=s)` calls are byte-identical (NFR-1)."""
    if _is_mock():
        from engine import mock_engine
        return mock_engine.initial_state(scenario=scenario, seed=seed)

    components = _components()
    drivers0 = Drivers(
        temp_C=20.0,
        humidity=0.5,
        pm25=0.0,
        psd_d50=20.0,
        voltage_stability=1.0,
        cycles=0,
        hours=0.0,
        maintenance_level={c: 1.0 for c in ComponentId},
        operator_shift="day",
        rng_seed=seed,
    )
    states = {
        cid: ComponentState(
            component_id=cid,
            health=1.0,
            status=status_for_health(1.0),
            metrics=components[cid].emit_metrics(
                ComponentState(
                    component_id=cid,
                    health=1.0,
                    status=status_for_health(1.0),
                    metrics={},
                ),
                drivers0,
            ),
        )
        for cid in ROW_ORDER
    }
    rng = np.random.default_rng(seed=int(seed))
    return EngineState(
        components=states,
        coupling_matrix=[list(row) for row in COUPLING_MATRIX_M],
        rng_state=tuple(_serialize_rng_state(rng)),
    )


def step(state: EngineState, drivers: Drivers, dt: float) -> EngineState:
    """Advance every component by `dt` simulated minutes.

    Pure function: same `(state, drivers, dt) -> same EngineState` (FR-1.5).
    Total wall time must remain < 50 ms on M3 Max CPU for all 6 components
    (NFR-2; benchmarked in `tests/engine/test_latency_step.py`).
    """
    if _is_mock():
        from engine import mock_engine
        return mock_engine.step(state, drivers, dt)
    if dt < 0:
        raise ValueError(f"dt must be non-negative, got {dt}")

    components = _components()
    rng = _restore_rng_state(state.rng_state)

    # 1) intrinsic decay per component (rule-based or PINN call).
    healths = np.array(
        [state.components[cid].health for cid in ROW_ORDER], dtype=np.float64
    )
    intrinsic = np.zeros(6, dtype=np.float64)
    for i, cid in enumerate(ROW_ORDER):
        intrinsic[i] = components[cid].intrinsic_decay(
            state.components[cid], drivers, dt, rng
        )

    # 2) matrix coupling (CSC-A and CSC-C ride here; CSC-B participates).
    new_healths = apply_coupling(healths, intrinsic, dt)

    # 3) CSC-B explicit physics layered on top of the matrix.
    heater = components[ComponentId.HEATER]
    field = heater._temp_field(drivers)
    swing, ambient_C, cycles_step = _csc_b.csc_b_inputs_from(
        drivers.temp_C, field, heater.duty_cycles_per_min, dt
    )
    new_healths = _csc_b.apply_csc_b(
        new_healths,
        heater_temp_swing_K=swing,
        enclosure_temp_C=ambient_C,
        duty_cycles_this_step=cycles_step,
        dt=dt,
    )

    # 4) re-emit metrics off the freshly-clamped healths.
    next_components = {}
    for i, cid in enumerate(ROW_ORDER):
        h = float(new_healths[i])
        next_components[cid] = ComponentState(
            component_id=cid,
            health=h,
            status=status_for_health(h),
            metrics=components[cid].emit_metrics(
                ComponentState(
                    component_id=cid, health=h, status=status_for_health(h), metrics={}
                ),
                drivers,
            ),
        )

    return EngineState(
        components=next_components,
        coupling_matrix=state.coupling_matrix,
        rng_state=tuple(_serialize_rng_state(rng)),
    )


def forecast(state: EngineState, horizon_min: int) -> List[Forecast]:
    """Return one Forecast per component at horizon_min (1..60)."""
    if _is_mock():
        from engine import mock_engine
        return mock_engine.forecast(state, horizon_min=horizon_min)
    if not (1 <= horizon_min <= 60):
        raise ValueError(
            f"horizon_min must be in [1, 60] per ADR-015, got {horizon_min}"
        )
    # Lazy import — the conformal layer pulls in sklearn/MAPIE which we
    # don't want to load for A1-A3 unit-only tests.
    from engine.conformal.wrapper import forecast_all_components

    return forecast_all_components(state, horizon_min=horizon_min)


# ---------------------------------------------------------------------------
# RNG state serialization helpers — ensure rng_state stays a hashable tuple
# in EngineState so two `step()` calls with the same input are byte-identical.
# ---------------------------------------------------------------------------

def _serialize_rng_state(rng: np.random.Generator) -> tuple:
    raw = rng.bit_generator.state
    return _freeze(raw)


def _restore_rng_state(serialized: tuple) -> np.random.Generator:
    rng = np.random.default_rng()
    rng.bit_generator.state = _thaw(serialized)
    return rng


def _freeze(obj):
    if isinstance(obj, dict):
        return tuple(sorted(((k, _freeze(v)) for k, v in obj.items())))
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze(x) for x in obj)
    if isinstance(obj, np.ndarray):
        return ("__ndarray__", obj.dtype.str, obj.shape, obj.tobytes())
    return obj


def _thaw(obj):
    if (
        isinstance(obj, tuple)
        and len(obj) == 4
        and obj[0] == "__ndarray__"
    ):
        _, dtype_str, shape, raw = obj
        return np.frombuffer(raw, dtype=np.dtype(dtype_str)).reshape(shape).copy()
    if isinstance(obj, tuple) and obj and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
        for item in obj
    ):
        return {k: _thaw(v) for k, v in obj}
    if isinstance(obj, tuple):
        return tuple(_thaw(x) for x in obj)
    return obj


__all__ = ["step", "forecast", "initial_state"]
