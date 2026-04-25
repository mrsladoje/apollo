"""Mock engine — PLAN-A §4 Step 0 deliverable.

Implements the exact `step` / `forecast` / `initial_state` signatures from
§3.2 against the real Pydantic schemas in `engine.contracts`. Plan B's sim
loop and Plan C's chat / UI build against this until real components ship.

Decay law (§4.1):
    health_i(t) = 1.0 - clip(α_i · t / 600, 0, 1)
with hand-set α_i so a 600-min Stressed run lands:
    heater FAILED ~min 480, nozzle FAILED ~min 520,
    blade & motor DEGRADED, insulation monotone, resistor CRITICAL by end.

Time t in minutes is derived from `Drivers.hours * 60` so step is a pure
function of (state, drivers, dt) — Plan B's loop owns time advancement and
the mock just reads the cumulative drivers value.
"""

from __future__ import annotations

import math

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


# ---------------------------------------------------------------------------
# Tunables (PLAN-A §4.1) — chosen so the 600-min Stressed run hits the
# qualitative milestones called out in the plan.
# ---------------------------------------------------------------------------

_RUN_LENGTH_MIN: float = 600.0  # denominator in the decay law

# alpha_i in the linear-time mock.
# At t=480: heater health = 1 - 1.15 * 0.8 = 0.08 -> FAILED.
# At t=520: nozzle health = 1 - 1.05 * (520/600) = ~0.09 -> FAILED.
# At t=600: blade=0.5 / motor=0.45 -> DEGRADED.
# At t=600: insulation=0.55 -> DEGRADED (monotone).
# At t=600: resistor=0.30 -> CRITICAL ("cycles up under shift load").
_ALPHA: dict[ComponentId, float] = {
    ComponentId.BLADE:      0.50,
    ComponentId.MOTOR:      0.55,
    ComponentId.NOZZLE:     1.05,
    ComponentId.RESISTOR:   0.70,
    ComponentId.HEATER:     1.15,
    ComponentId.INSULATION: 0.45,
}


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _health_at(component: ComponentId, t_min: float) -> float:
    """Synthetic decay curve from §4.1."""
    alpha = _ALPHA[component]
    return 1.0 - _clip(alpha * t_min / _RUN_LENGTH_MIN, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Mock PINN (§4.1) — pure NumPy-free sigmoid, < 0.1 ms.
# ---------------------------------------------------------------------------

def mock_pinn(temp_C: float, hours: float) -> float:
    """Returns drift_pct in [0, 0.4] as a deterministic function of hours."""
    z = (hours - 6.0) / 1.5
    sigmoid = 1.0 / (1.0 + math.exp(-z))
    return sigmoid * 0.4


# ---------------------------------------------------------------------------
# Mock MAPIE (§4.1) — band widens with sqrt(horizon), clamped to [0, 1].
# ---------------------------------------------------------------------------

def _mock_mapie(point: float, horizon_min: int) -> tuple[float, float]:
    half_width = 0.05 * math.sqrt(horizon_min)
    return _clip(point - half_width, 0.0, 1.0), _clip(point + half_width, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Per-component metric synthesizers — keys per PLAN-A §6.3.
# ---------------------------------------------------------------------------

def _metrics_for(component: ComponentId, health: float, drivers: Drivers) -> dict[str, float]:
    if component is ComponentId.BLADE:
        return {
            "blade_thickness_mm": round(1.00 * health, 6),
            "impact_count": float(int((1.0 - health) * 1000)),
        }
    if component is ComponentId.MOTOR:
        return {
            "current_draw_A": round(5.0 + 3.0 * (1.0 - health), 6),
            "bearing_temp_C": round(60.0 + 40.0 * (1.0 - health), 6),
        }
    if component is ComponentId.NOZZLE:
        return {
            "clog_prob": round(_clip(1.0 - health, 0.0, 1.0), 6),
            "active_nozzle_count": float(int(1024 * health)),
        }
    if component is ComponentId.RESISTOR:
        return {
            "resistance_pct": round(100.0 - 5.0 * (1.0 - health), 6),
        }
    if component is ComponentId.HEATER:
        drift = mock_pinn(drivers.temp_C, drivers.hours)
        hot_side = drivers.temp_C + 100.0 * (1.0 - 0.3 * (1.0 - health))
        return {
            "drift_pct": round(drift, 6),
            "predicted_temp_field_x0_C": round(hot_side, 6),
            "predicted_temp_field_xmid_C": round((hot_side + drivers.temp_C) / 2.0, 6),
            "predicted_temp_field_xL_C": round(drivers.temp_C, 6),
        }
    if component is ComponentId.INSULATION:
        return {
            "k_eff_W_mK": round(0.05 * health, 6),
        }
    raise ValueError(f"unknown component {component!r}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Public surface (§3.2) — `step`, `forecast`, `initial_state`.
# ---------------------------------------------------------------------------

def initial_state(scenario: str = "default", seed: int = 0) -> EngineState:
    """Construct a fresh EngineState with all 6 components at health=1.0.

    The mock's `rng_state` is `(seed, scenario)` — opaque tuple, satisfies
    the contract. Real engine will store a serialized np.random.Generator
    state here.
    """
    drivers_at_t0 = Drivers(
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
    components = {
        cid: ComponentState(
            component_id=cid,
            health=1.0,
            status=status_for_health(1.0),
            metrics=_metrics_for(cid, 1.0, drivers_at_t0),
        )
        for cid in ComponentId
    }
    return EngineState(
        components=components,
        coupling_matrix=[list(row) for row in COUPLING_MATRIX_M],
        rng_state=(int(seed), str(scenario)),
        events=(),
    )


def step(state: EngineState, drivers: Drivers, dt: float) -> EngineState:
    """Advance every component by `dt` simulated minutes.

    Pure function: same (state, drivers, dt) → same EngineState (FR-1.5).
    The mock derives sim time from `drivers.hours * 60`; Plan B's loop is
    responsible for advancing `drivers.hours += dt / 60.0` between calls.
    `dt` is accepted for signature stability and validated to be >= 0.
    """
    if dt < 0:
        raise ValueError(f"dt must be non-negative, got {dt}")

    t_min = max(0.0, drivers.hours) * 60.0
    next_components: dict[ComponentId, ComponentState] = {}
    for cid in ROW_ORDER:
        h = _health_at(cid, t_min)
        next_components[cid] = ComponentState(
            component_id=cid,
            health=h,
            status=status_for_health(h),
            metrics=_metrics_for(cid, h, drivers),
        )
    return EngineState(
        components=next_components,
        coupling_matrix=state.coupling_matrix,
        rng_state=state.rng_state,
        events=(),
    )


def forecast(state: EngineState, horizon_min: int) -> list[Forecast]:
    """Return one Forecast per component at horizon_min (1..60).

    ADR-015 cap: rejects horizon_min > 60 with ValueError. The mock band is
    `(point, point ± 0.05 * sqrt(horizon))` clamped to [0, 1] — widens with
    horizon so Plan C's Recharts shaded `Area` reads correctly.
    """
    if horizon_min < 1 or horizon_min > 60:
        raise ValueError(
            f"horizon_min must be in [1, 60] per ADR-015, got {horizon_min}"
        )

    # Mock predictor: project current health forward linearly using the
    # component's α and the horizon, with t derived from rng_state[0] *
    # 0 + current EngineState (we don't have a clock here, so we use the
    # observed health as the anchor and decay it for `horizon_min` more).
    forecasts: list[Forecast] = []
    for cid in ROW_ORDER:
        current_h = state.components[cid].health
        delta = _ALPHA[cid] * horizon_min / _RUN_LENGTH_MIN
        point = _clip(current_h - delta, 0.0, 1.0)
        lower, upper = _mock_mapie(point, horizon_min)
        forecasts.append(
            Forecast(
                component_id=cid,
                horizon_min=horizon_min,
                point=point,
                lower=lower,
                upper=upper,
                ci_level=0.95,
            )
        )
    return forecasts


__all__ = ["step", "forecast", "initial_state", "mock_pinn"]
