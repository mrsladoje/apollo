"""PLAN-C §9 / FR-W.7 — every Apollo response carries a Langfuse trace_url."""

from __future__ import annotations

import os
import re

from apollo.agent.loop import AgentLoop
from apollo.agent.observability import langfuse_host, trace_url_for


def test_trace_url_present_on_every_response(historian_db_path) -> None:
    loop = AgentLoop(db_path=historian_db_path)
    for q in [
        "How is the barcelona-humid-ai-seed0042 nozzle?",
        "What is the weather in Madrid?",
    ]:
        resp = loop.answer(q)
        assert resp.trace_url, q
        assert resp.trace_url.startswith(("http://", "https://"))


def test_self_hosted_fallback_url() -> None:
    os.environ["LANGFUSE_HOST"] = "http://localhost:3000"
    try:
        url = trace_url_for("any-query")
        assert url.startswith("http://localhost:3000/trace/")
        assert re.match(r".*/trace/[0-9a-f]{32}$", url)
    finally:
        del os.environ["LANGFUSE_HOST"]


def test_langfuse_host_default() -> None:
    if "LANGFUSE_HOST" in os.environ:
        del os.environ["LANGFUSE_HOST"]
    assert langfuse_host() == "https://cloud.langfuse.com"
