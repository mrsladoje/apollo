"""Live-loop routing guards for named policy comparisons."""

from __future__ import annotations

import asyncio

from apollo.agent import live_loop


async def _collect(events):
    return [event async for event in events]


def test_policy_compare_aliases_map_to_canonical_runs() -> None:
    run_ids = live_loop._infer_compare_run_ids("Can you compare Apollo and dark twin?", None)

    assert run_ids == [
        "barcelona-humid-ai-seed0042",
        "barcelona-humid-none-seed0042",
    ]
    assert live_loop._wants_run_comparison("Can you compare Apollo and dark twin?", None)


def test_live_policy_compare_bypasses_router_refusal(monkeypatch, historian_db_path) -> None:
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")

    def fake_complete(system_prompt: str, prompt: str, runtime_lm: str, *, max_tokens: int) -> str:
        assert "Available tools. Return exactly one JSON object" not in prompt
        return '{"severity":"REFUSAL","text":"REFUSAL - cannot answer","citations":[]}'

    monkeypatch.setattr(live_loop, "_complete", fake_complete)

    events = asyncio.run(
        _collect(
            live_loop.stream_live_events(
                query="Can you compare Apollo and dark twin?",
                run_context=None,
                db_path=historian_db_path,
                cap=3,
                system_prompt="",
                runtime_lm="models/gemma-4-31b-it",
            )
        )
    )

    starts = [event for event in events if event["type"] == "tool-call-start"]
    assert starts[0]["payload"]["tool"] == "compare_runs"
    assert starts[0]["payload"]["args"]["run_ids"] == [
        "barcelona-humid-ai-seed0042",
        "barcelona-humid-none-seed0042",
    ]

    text = "".join(event["payload"]["token"] for event in events if event["type"] == "text-delta")
    assert "Apollo" in text
    assert "dark twin" in text
    assert not text.startswith("REFUSAL")


def test_live_apollo_plot_without_component_plots_all_components(monkeypatch, historian_db_path) -> None:
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")

    def fake_complete(system_prompt: str, prompt: str, runtime_lm: str, *, max_tokens: int) -> str:
        assert "Available tools. Return exactly one JSON object" not in prompt
        return '{"severity":"REFUSAL","text":"REFUSAL - cannot answer","citations":[]}'

    monkeypatch.setattr(live_loop, "_complete", fake_complete)

    events = asyncio.run(
        _collect(
            live_loop.stream_live_events(
                query="Please plot apollo",
                run_context=None,
                db_path=historian_db_path,
                cap=3,
                system_prompt="",
                runtime_lm="models/gemma-4-31b-it",
            )
        )
    )

    starts = [event for event in events if event["type"] == "tool-call-start"]
    assert [event["payload"]["tool"] for event in starts] == ["plot_component_history"] * 6
    assert {event["payload"]["args"]["run_id"] for event in starts} == {
        "barcelona-humid-ai-seed0042",
    }

    text = "".join(event["payload"]["token"] for event in events if event["type"] == "text-delta")
    assert "Apollo" in text
    assert "blade" in text
    assert "motor" in text
    assert not text.startswith("REFUSAL")
