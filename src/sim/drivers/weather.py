"""Weather + air-pollution providers — PLAN-B §6.1.

Demo path is offline-only (R-7): live API calls are disabled and we read
from the CSVs cached by ``sim.drivers.cache_all`` in pre-demo. Each row in
``data/weather/{city}.csv`` and ``data/air/{city}.csv`` carries one
hour-resolution sample; providers interpolate to the requested ``t``.

Setting ``OPENWEATHER_API_KEY`` in the environment switches the providers
to live mode (``cache_all`` only). The simulation loop never reaches into
the network.
"""

from __future__ import annotations

import csv
import os
from bisect import bisect_left
from datetime import datetime
from typing import Dict, List, Optional, Tuple

WEATHER_DIR = "data/weather"
AIR_DIR = "data/air"


def _read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _interp(rows: List[Dict[str, str]], t: datetime, key: str) -> Optional[float]:
    """Stepwise interpolation against an hour-resolution table."""
    if not rows:
        return None
    times: List[datetime] = [datetime.fromisoformat(r["t"]) for r in rows]
    values: List[float] = [float(r[key]) for r in rows]
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    idx = bisect_left(times, t)
    # Linear blend between the two enclosing hours.
    t0, t1 = times[idx - 1], times[idx]
    v0, v1 = values[idx - 1], values[idx]
    span = (t1 - t0).total_seconds() or 1.0
    frac = (t - t0).total_seconds() / span
    return v0 + (v1 - v0) * frac


class MockWeatherProvider:
    """Reads pre-cached weather CSVs (R-7 mitigation)."""

    def __init__(self, weather_dir: str = WEATHER_DIR) -> None:
        self.weather_dir = weather_dir
        self._cache: Dict[str, List[Dict[str, str]]] = {}

    def _rows(self, city: str) -> List[Dict[str, str]]:
        if city not in self._cache:
            self._cache[city] = _read_csv(os.path.join(self.weather_dir, f"{city}.csv"))
        return self._cache[city]

    def get(self, t: datetime, city: str) -> Optional[Tuple[float, float]]:
        rows = self._rows(city)
        if not rows:
            return None
        temp = _interp(rows, t, "temp_C")
        humidity = _interp(rows, t, "humidity")
        if temp is None or humidity is None:
            return None
        return float(temp), float(humidity)


class MockAirPollutionProvider:
    """Reads pre-cached PM2.5 CSVs (R-7 mitigation)."""

    def __init__(self, air_dir: str = AIR_DIR) -> None:
        self.air_dir = air_dir
        self._cache: Dict[str, List[Dict[str, str]]] = {}

    def _rows(self, city: str) -> List[Dict[str, str]]:
        if city not in self._cache:
            self._cache[city] = _read_csv(os.path.join(self.air_dir, f"{city}.csv"))
        return self._cache[city]

    def get(self, t: datetime, city: str) -> Optional[float]:
        rows = self._rows(city)
        if not rows:
            return None
        pm25 = _interp(rows, t, "pm25")
        return None if pm25 is None else float(pm25)


__all__ = [
    "MockWeatherProvider",
    "MockAirPollutionProvider",
    "WEATHER_DIR",
    "AIR_DIR",
]
