"""PLAN-C §8.4 — six template-bounded speak() generators (ADR-019)."""

from __future__ import annotations

import pytest

from apollo.agent.speak import TEMPLATES, speak, speak_for_component
from engine.contracts import ComponentId, ComponentState, ComponentStatus

# Engine-shaped metric bundles so speak() exercises the real metric keys.
COMPONENT_METRICS: dict[ComponentId, dict[str, float]] = {
    ComponentId.BLADE: {"blade_thickness_mm": 0.62, "impact_count": 4000},
    ComponentId.MOTOR: {"current_draw_A": 7.0, "bearing_temp_C": 88.0},
    ComponentId.NOZZLE: {"clog_prob": 0.18, "active_nozzle_count": 980},
    ComponentId.RESISTOR: {"resistance_pct": 95.4, "thermal_cycles": 1200},
    ComponentId.HEATER: {"drift_pct": 0.04, "predicted_temp_field_x0_C": 110},
    ComponentId.INSULATION: {"k_eff_W_mK": 0.072, "loss": 0.1},
}

AFFECTIVE_WORDS = {
    "wow", "oh", "alas", "danger", "alarm", "panic",
    "ugh", "crisis", "emergency", "brilliant", "lovely",
}


@pytest.mark.parametrize("component", list(ComponentId))
def test_speak_emits_grounded_sentence(component: ComponentId) -> None:
    metrics = COMPONENT_METRICS[component]
    state = ComponentState(
        component_id=component,
        health=0.6,
        status=ComponentStatus.DEGRADED,
        metrics=metrics,
    )
    sentence = speak(state)
    assert sentence.startswith("My "), sentence
    assert sentence.endswith("."), sentence
    # No exclamation, no affective vocabulary.
    assert "!" not in sentence
    lowered = sentence.lower()
    assert not any(w in lowered for w in AFFECTIVE_WORDS)


def test_six_templates_one_per_component() -> None:
    assert set(TEMPLATES) == {c.value for c in ComponentId}


def test_speak_for_component_round_trip() -> None:
    metrics = COMPONENT_METRICS[ComponentId.NOZZLE]
    s = speak_for_component(ComponentId.NOZZLE, metrics)
    assert "nozzle" in s.lower()
    assert "%" in s  # clog_prob renders as percent
