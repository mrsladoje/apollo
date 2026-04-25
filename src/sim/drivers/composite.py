"""Composite driver provider — PLAN-B §6.

Each ``get(t, scenario, seed)`` call must be deterministic in
``(scenario, seed, t)`` (asserted by ``test_composite_determinism``). The
provider composes:

- ``MockWeatherProvider`` (CSV-backed, §6.1)
- ``MockAirPollutionProvider`` (CSV-backed, §6.1)
- A synthetic powder-PSD genealogy
- A synthetic operator-shift calendar
- A synthetic voltage-stability noise model
- An operational-load model derived from elapsed sim time

CSVs (when present) are the source of truth for weather and PM2.5; if the
CSV is missing for a scenario the provider falls back to a deterministic
synthetic trajectory so unit tests run without ``cache_all`` being called.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Literal, Optional

from engine.contracts import ComponentId, Drivers

from .base import DriverProvider
from .weather import MockAirPollutionProvider, MockWeatherProvider

# Wall-clock anchor — matches ``sim.loop.SIM_START_TIME``.
SIM_START_TIME = datetime(2026, 4, 25, 8, 0, 0)

# Maps each scenario to the weather/air city key (None = no CSV, fully
# synthetic). The "stressed" scenario is genuinely synthetic per §8.1.
_SCENARIO_CITY = {
    "barcelona-humid": "barcelona",
    "phoenix-dry": "phoenix",
    "stressed": None,
}


def _seeded_rng(scenario_name: str, seed: int, t: datetime) -> random.Random:
    return random.Random(f"{scenario_name}-{seed}-{t.isoformat()}")


def _operator_shift(t: datetime) -> Literal["day", "night", "weekend"]:
    if t.weekday() >= 5:
        return "weekend"
    if 6 <= t.hour < 18:
        return "day"
    return "night"


def _synthetic_weather(scenario_name: str, t: datetime, rng: random.Random) -> tuple:
    """Fallback for when no CSV is present (e.g. ``stressed``)."""
    if scenario_name == "barcelona-humid":
        base_temp, base_humidity = 22.0, 0.78
    elif scenario_name == "phoenix-dry":
        base_temp, base_humidity = 35.0, 0.18
    else:  # stressed
        base_temp, base_humidity = 25.0, 0.65
    hour = t.hour + t.minute / 60.0
    diurnal = 5.0 * (1.0 - abs(hour - 14.0) / 12.0)
    return base_temp + diurnal, base_humidity


def _synthetic_pm25(scenario_name: str, rng: random.Random) -> float:
    if scenario_name == "barcelona-humid":
        return 15.0 + 10.0 * rng.random()
    if scenario_name == "phoenix-dry":
        return 5.0 + 5.0 * rng.random()
    return 40.0 + 20.0 * rng.random()  # stressed


def _psd_d50(scenario_name: str, elapsed_hours: float) -> float:
    """Powder-particle D50 genealogy.

    §6.1 PowderPSDProvider: ``D50 = f(powder_age_days, storage_humidity)``.
    Stressed scenario degrades powder twice as fast (``psd_degradation_rate=2``
    per §8.1).
    """
    age_days = elapsed_hours / 24.0
    base = 20.0
    rate = 2.0 if scenario_name == "stressed" else 1.0
    return base + 0.05 * rate * age_days * 24.0  # gentle drift


class CompositeDriverProvider(DriverProvider):
    """Synthetic + CSV-backed driver trajectory keyed by ``(scenario, seed, t)``."""

    def __init__(
        self,
        weather: Optional[MockWeatherProvider] = None,
        air: Optional[MockAirPollutionProvider] = None,
    ) -> None:
        self._weather = weather or MockWeatherProvider()
        self._air = air or MockAirPollutionProvider()

    def get(self, t: datetime, scenario_name: str, seed: int) -> Drivers:
        rng = _seeded_rng(scenario_name, seed, t)
        city = _SCENARIO_CITY.get(scenario_name)

        # Weather: CSV-first (R-7), synthetic fallback.
        if city is not None:
            wx = self._weather.get(t, city)
        else:
            wx = None
        if wx is None:
            temp_C, humidity = _synthetic_weather(scenario_name, t, rng)
        else:
            temp_C, humidity = wx
            # Add tiny scenario-and-seed-keyed jitter so re-running with a
            # different seed still produces a different trajectory.
            temp_C += rng.uniform(-0.2, 0.2)

        # PM2.5: CSV-first.
        if city is not None:
            pm25 = self._air.get(t, city)
        else:
            pm25 = None
        if pm25 is None:
            pm25 = _synthetic_pm25(scenario_name, rng)

        elapsed_hours = max(0.0, (t - SIM_START_TIME).total_seconds() / 3600.0)
        psd_d50 = _psd_d50(scenario_name, elapsed_hours)

        # Voltage stability: tiny Gaussian noise around 0.97 + occasional
        # dropouts at deterministic minute boundaries (seeded).
        voltage_stability = 0.97 + rng.gauss(0.0, 0.01)
        if rng.random() < 0.005:
            voltage_stability *= 0.85
        voltage_stability = max(0.0, min(1.0, voltage_stability))

        return Drivers(
            temp_C=float(temp_C),
            humidity=float(humidity),
            pm25=float(pm25),
            psd_d50=float(psd_d50),
            voltage_stability=float(voltage_stability),
            cycles=int(elapsed_hours * 10),
            hours=elapsed_hours,
            maintenance_level={cid: 1.0 for cid in ComponentId},
            operator_shift=_operator_shift(t),
            rng_seed=seed,
        )


__all__ = ["CompositeDriverProvider", "SIM_START_TIME"]
