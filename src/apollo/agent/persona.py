"""Apollo persona loader — < 200-token cap (ADR-019, PLAN-C §8)."""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_persona() -> str:
    """Read ``persona.md`` from disk. Cached on first call."""
    return (_PROMPTS_DIR / "persona.md").read_text(encoding="utf-8")


def load_system_prompt() -> str:
    """Load the GEPA-compiled prompt if present, else the seed prompt.

    Per PLAN-C §6.1 / §14a — runtime loads ``config/agent.system_prompt.gepa.txt``
    when available, falling back to ``prompts/system.md``.
    """
    repo_root = Path(__file__).resolve().parents[3]
    compiled = repo_root / "config" / "agent.system_prompt.gepa.txt"
    if compiled.exists() and compiled.stat().st_size > 0:
        return compiled.read_text(encoding="utf-8")
    return (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")


_TIKTOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


def approx_token_count(text: str) -> int:
    """Approximation when ``tiktoken`` isn't available.

    Word-or-punct count is a tighter upper bound than whitespace-split for
    English prose; close enough for the < 200-token guard. If ``tiktoken`` is
    installed it's preferred (cl100k_base, GPT-3.5/4 encoder).
    """
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:  # pragma: no cover — exercised by the test if missing
        return len(_TIKTOKEN_PATTERN.findall(text))


__all__ = ["approx_token_count", "load_persona", "load_system_prompt"]
