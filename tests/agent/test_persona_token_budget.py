"""PLAN-C §8.1 — Apollo persona prompt < 200 tokens (ADR-019)."""

from __future__ import annotations

from apollo.agent.persona import approx_token_count, load_persona


def test_under_200_tokens() -> None:
    persona = load_persona()
    n = approx_token_count(persona)
    assert n < 200, f"persona prompt too long: {n} tokens"


def test_persona_voice_rules_present() -> None:
    persona = load_persona()
    assert "Calm" in persona
    assert "Dark Twin" in persona
    assert "first person" in persona
    assert "!" not in persona  # no exclamation marks
