"""NFR-5 — agent response p95 < 6 s on the canonical query."""

from __future__ import annotations

import time

import pytest

from apollo.agent.loop import AgentLoop


@pytest.fixture(scope="module")
def loop(historian_db_path) -> AgentLoop:
    return AgentLoop(db_path=historian_db_path)


def test_canonical_latency_p95_under_6s(loop: AgentLoop) -> None:
    samples = []
    for _ in range(5):
        t0 = time.perf_counter()
        loop.answer(
            "How is the barcelona-humid-ai-seed0042 nozzle?",
            run_context="barcelona-humid-ai-seed0042",
        )
        samples.append(time.perf_counter() - t0)
    samples.sort()
    p95 = samples[max(0, int(len(samples) * 0.95) - 1)]
    assert p95 < 6.0, f"p95 latency {p95:.2f}s ≥ 6s"
