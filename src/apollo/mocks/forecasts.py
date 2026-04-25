"""Forecasts mock loader (PLAN-C §4.1)."""

from __future__ import annotations

import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "forecasts_mock.json"


def load_forecasts() -> dict:
    return json.loads(_PATH.read_text(encoding="utf-8"))


__all__ = ["load_forecasts"]
