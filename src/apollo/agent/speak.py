"""Component speak() generators (PLAN-C §8.3, ADR-019).

Each generator consumes a ``ComponentState`` row and emits a single
first-person sentence drawn from a fixed templates list — no LLM call, no
free-form generation, so they cannot hallucinate. The templates themselves
match PLAN-C §8.3 verbatim; this module bridges the engine's actual metric
keys (e.g. ``blade_thickness_mm``) to the template parameter names
(``thickness``, ``temp``, ``prob`` etc).

Component identifiers are imported from ``engine.contracts.ComponentId`` —
no bare string literals, per ADR-021 / PLAN-C §20.8.
"""

from __future__ import annotations

from typing import Mapping

from engine.contracts import ComponentId, ComponentState

# Templates pinned to PLAN-C §8.3. Keys are ``ComponentId`` enum values to
# satisfy the no-string-component-names architecture lint.
TEMPLATES: dict[ComponentId, str] = {
    ComponentId.BLADE:      "My blade is {thickness:.2f} mm thick — {delta:.2f} mm below spec.",
    ComponentId.MOTOR:      "My bearing is at {temp:.0f} °C; that's {band} my comfort band.",
    ComponentId.NOZZLE:     "My clog probability is {prob:.0%}; {n_active} of 1024 nozzles are firing.",
    ComponentId.RESISTOR:   "My resistance is {pct:.1f}% of nominal after {cycles} thermal cycles.",
    ComponentId.HEATER:     "My predicted temperature drift is {drift:.1f}% — PINN says I'm within physics bounds.",
    ComponentId.INSULATION: "My k_eff is {keff:.3f} W/m·K; insulation has lost {loss:.0%} of nominal performance.",
}

_BLADE_SPEC_MM = 1.0
_MOTOR_COMFORT_C = 95.0
_INSULATION_NOMINAL = 0.08
_NOZZLE_TOTAL = 1024


def _blade_args(metrics: Mapping[str, float]) -> dict[str, float]:
    thickness = float(metrics.get("blade_thickness_mm", metrics.get("thickness", 0.0)))
    return {"thickness": thickness, "delta": max(0.0, _BLADE_SPEC_MM - thickness)}


def _motor_args(metrics: Mapping[str, float]) -> dict[str, object]:
    temp = float(metrics.get("bearing_temp_C", metrics.get("temp", 0.0)))
    band = "below" if temp <= _MOTOR_COMFORT_C else "above"
    return {"temp": temp, "band": band}


def _nozzle_args(metrics: Mapping[str, float]) -> dict[str, object]:
    prob = float(metrics.get("clog_prob", metrics.get("prob", 0.0)))
    active = int(metrics.get("active_nozzle_count", metrics.get("n_active", _NOZZLE_TOTAL)))
    return {"prob": prob, "n_active": active}


def _resistor_args(metrics: Mapping[str, float]) -> dict[str, object]:
    pct = float(metrics.get("resistance_pct", metrics.get("pct", 100.0)))
    cycles = int(metrics.get("thermal_cycles", metrics.get("cycles", 0)))
    return {"pct": pct, "cycles": cycles}


def _heater_args(metrics: Mapping[str, float]) -> dict[str, float]:
    drift = float(metrics.get("drift_pct", metrics.get("drift", 0.0)))
    return {"drift": drift * 100.0 if drift <= 1.0 else drift}


def _insulation_args(metrics: Mapping[str, float]) -> dict[str, float]:
    keff = float(metrics.get("k_eff_W_mK", metrics.get("keff", _INSULATION_NOMINAL)))
    loss = max(0.0, 1.0 - (keff / _INSULATION_NOMINAL)) if _INSULATION_NOMINAL else 0.0
    return {"keff": keff, "loss": loss}


_RENDERERS = {
    ComponentId.BLADE: _blade_args,
    ComponentId.MOTOR: _motor_args,
    ComponentId.NOZZLE: _nozzle_args,
    ComponentId.RESISTOR: _resistor_args,
    ComponentId.HEATER: _heater_args,
    ComponentId.INSULATION: _insulation_args,
}


def speak(state: ComponentState) -> str:
    """Render a single first-person sentence for ``state``."""
    cid = (
        state.component_id
        if isinstance(state.component_id, ComponentId)
        else ComponentId(state.component_id)
    )
    template = TEMPLATES[cid]
    args = _RENDERERS[cid](state.metrics or {})
    return template.format(**args)


def speak_for_component(component: ComponentId, metrics: Mapping[str, float]) -> str:
    """Variant for callers that don't have a ``ComponentState`` handy."""
    cid = component if isinstance(component, ComponentId) else ComponentId(component)
    template = TEMPLATES[cid]
    return template.format(**_RENDERERS[cid](metrics))


__all__ = ["TEMPLATES", "speak", "speak_for_component"]
