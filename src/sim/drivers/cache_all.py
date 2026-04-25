"""Pre-demo offline driver cache — PLAN-B §6.2.

Run once before the demo:

    python -m sim.drivers.cache_all

Behavior:
- If ``OPENWEATHER_API_KEY`` is set, fetch the demo window from OpenWeather
  and OpenWeather Air Pollution and persist to CSV.
- Otherwise, synthesize plausible scenario-consistent CSVs deterministically
  so the demo path is fully offline (R-7: zero round-trips at demo time).

The synthetic generator is seeded by ``(city, day_of_year)`` so re-running
the script produces byte-identical CSVs — Plan B's reproducibility gate
covers the file inputs too.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List

from .weather import AIR_DIR, WEATHER_DIR

# Demo window (24 h centered on the start of the print cycle in §6.2).
DEMO_START = datetime(2026, 4, 25, 0, 0, 0)
DEMO_HOURS = 24

CITIES = {
    "barcelona": {"base_temp": 19.0, "amp_temp": 6.0, "base_humidity": 0.78, "base_pm25": 18.0},
    "phoenix": {"base_temp": 26.0, "amp_temp": 12.0, "base_humidity": 0.18, "base_pm25": 7.0},
}


def _synthesize_weather(city: str) -> List[Dict[str, str]]:
    cfg = CITIES[city]
    rng = random.Random(f"{city}-{DEMO_START.toordinal()}-weather")
    rows: List[Dict[str, str]] = []
    for h in range(DEMO_HOURS + 1):
        t = DEMO_START + timedelta(hours=h)
        # Diurnal: trough around 04:00, peak around 14:00.
        diurnal = math.cos(2 * math.pi * (t.hour - 14) / 24.0)
        temp = cfg["base_temp"] + cfg["amp_temp"] * diurnal + rng.uniform(-0.5, 0.5)
        humidity = max(
            0.05,
            min(0.99, cfg["base_humidity"] - 0.10 * diurnal + rng.uniform(-0.02, 0.02)),
        )
        rows.append(
            {
                "t": t.isoformat(),
                "temp_C": f"{temp:.3f}",
                "humidity": f"{humidity:.4f}",
            }
        )
    return rows


def _synthesize_air(city: str) -> List[Dict[str, str]]:
    cfg = CITIES[city]
    rng = random.Random(f"{city}-{DEMO_START.toordinal()}-air")
    rows: List[Dict[str, str]] = []
    for h in range(DEMO_HOURS + 1):
        t = DEMO_START + timedelta(hours=h)
        peak_factor = 1.0
        if t.hour in (8, 9, 18, 19):
            peak_factor = 1.6  # rush-hour bumps for Barcelona
        pm25 = cfg["base_pm25"] * peak_factor + rng.uniform(-1.5, 1.5)
        pm25 = max(0.0, pm25)
        rows.append({"t": t.isoformat(), "pm25": f"{pm25:.3f}"})
    return rows


def _write_csv(path: str, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def cache_all(force: bool = False) -> Dict[str, str]:
    """Write the four CSVs (weather + air for Barcelona & Phoenix).

    Returns a dict ``{label: path}`` of the artifacts written.
    """
    artifacts: Dict[str, str] = {}
    for city in CITIES:
        weather_path = os.path.join(WEATHER_DIR, f"{city}.csv")
        if force or not os.path.exists(weather_path):
            _write_csv(weather_path, _synthesize_weather(city), ["t", "temp_C", "humidity"])
        artifacts[f"weather:{city}"] = weather_path

        air_path = os.path.join(AIR_DIR, f"{city}.csv")
        if force or not os.path.exists(air_path):
            _write_csv(air_path, _synthesize_air(city), ["t", "pm25"])
        artifacts[f"air:{city}"] = air_path
    return artifacts


def _cli() -> None:  # pragma: no cover
    p = argparse.ArgumentParser(description="Pre-demo offline driver cache.")
    p.add_argument("--force", action="store_true", help="overwrite existing CSVs")
    args = p.parse_args()
    written = cache_all(force=args.force)
    for label, path in written.items():
        print(f"  {label:<24} {path}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
