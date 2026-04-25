"""PLAN-C §6.1 / ADR-022 — config/agent.yaml pins Gemma 4 31B."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG = REPO_ROOT / "config" / "agent.yaml"


def test_config_pins_gemma() -> None:
    assert CFG.exists(), "config/agent.yaml missing"
    text = CFG.read_text(encoding="utf-8")
    assert "google/gemma-4-31B" in text, "runtime LM is not Gemma 4 31B"


def test_config_yaml_parses() -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        import pytest

        pytest.skip("PyYAML not installed")
    data = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    assert data["model"].startswith("google/gemma-4-31B")
    assert int(data["max_tool_calls_per_turn"]) == 3
