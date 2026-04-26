"""ClaudeCLI — thin DSPy ``LM`` subclass that shells out to the local ``claude``
binary for Claude Opus 4.7 reflections (PLAN-C §14a.3, ADR-022).

We intentionally do not import ``dspy`` at module import time so the agent
stays usable without DSPy installed; the class falls back to ``object`` and
just exposes ``__call__`` / ``generate`` / ``request`` shaped like a DSPy LM.
The GEPA compile script (`scripts/agent/compile_prompt.py`) is the only
caller that depends on the real DSPy types.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Iterable, Optional

try:  # pragma: no cover — import guard
    import dspy  # type: ignore

    _DSPY_BASE = dspy.LM
except Exception:  # pragma: no cover — fallback when DSPy isn't installed
    _DSPY_BASE = object  # type: ignore


class ClaudeCLI(_DSPY_BASE):  # type: ignore[misc]
    """Reflection LM for ``dspy.GEPA``.

    Shells out to ``claude --print --model <model> <prompt>``. ``claude`` is
    expected on the PATH (already installed for Claude Code users).
    """

    def __init__(
        self,
        model: str = "",
        cli: str | None = None,
        extra_args: Optional[Iterable[str]] = None,
        max_chars: int = 8192,
    ) -> None:
        if _DSPY_BASE is not object:  # pragma: no cover — exercised under dspy
            super().__init__(model=f"claude_cli/{model}")
        self.model = model
        self.cli = cli or os.environ.get("CLAUDE_CLI", "claude")
        self.extra_args = list(extra_args or [])
        self.max_chars = max_chars
        self.history: list[dict[str, Any]] = []
        self.kwargs: dict[str, Any] = {}

    # ----- DSPy compatibility surface ------------------------------------
    def __call__(
        self,
        prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **_: Any,
    ) -> list[str]:
        text = prompt
        if text is None and messages:
            text = "\n\n".join(m.get("content", "") for m in messages)
        if text is None:
            text = ""
        return [self._invoke(text)]

    def generate(self, prompt: str, **_: Any) -> str:
        return self._invoke(prompt)

    def request(self, prompt: str, **_: Any) -> str:
        return self._invoke(prompt)

    # ----- internals -----------------------------------------------------
    def _invoke(self, prompt: str) -> str:
        truncated = prompt[: self.max_chars]
        cmd = [self.cli, "--print", *self.extra_args]
        if self.model:
            cmd.extend(["--model", self.model])
        cmd.append(truncated)
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                input="",
                text=True,
                timeout=300,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"`{self.cli}` binary not found on PATH; install Claude CLI "
                "or set CLAUDE_CLI env var."
            ) from exc
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (rc={proc.returncode}): {proc.stderr.strip()}"
            )
        out = proc.stdout.strip()
        self.history.append({"prompt": truncated, "completion": out})
        return out


__all__ = ["ClaudeCLI"]
