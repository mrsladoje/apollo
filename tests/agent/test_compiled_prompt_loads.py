"""PLAN-C §14a / FR-W.10 — agent loads the GEPA-compiled prompt."""

from __future__ import annotations

from pathlib import Path

from apollo.agent.persona import approx_token_count, load_system_prompt

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPILED = REPO_ROOT / "config" / "agent.system_prompt.gepa.txt"
LOG = REPO_ROOT / "docs" / "eval" / "gepa_compile_log.json"


def test_compiled_prompt_artifact_exists() -> None:
    assert COMPILED.exists(), "GEPA-compiled prompt artifact missing"
    assert COMPILED.stat().st_size > 0


def test_gepa_compile_log_exists() -> None:
    assert LOG.exists(), "gepa_compile_log.json missing"


def test_compiled_prompt_under_800_tokens() -> None:
    text = COMPILED.read_text(encoding="utf-8")
    n = approx_token_count(text)
    assert n < 800, f"compiled prompt is {n} tokens (> 800 ceiling)"


def test_runtime_loads_compiled_prompt() -> None:
    seed_path = REPO_ROOT / "src" / "apollo" / "agent" / "prompts" / "system.md"
    seed = seed_path.read_text(encoding="utf-8")
    runtime = load_system_prompt()
    # GEPA-compiled prompt must be a strict superset (or distinct) of the seed.
    assert runtime != seed, "runtime is using the seed prompt instead of compiled"
    assert "GEPA-compiled" in runtime or runtime.startswith(seed[:80])
