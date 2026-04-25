import random
from datetime import datetime
from typing import Literal
from engine.contracts import Drivers, ComponentId
from .base import DriverProvider

class CompositeDriverProvider:
    def __init__(self):
        # In a real impl, this would compose sub-providers
        pass

    def get(self, t: datetime, scenario_name: str, seed: int) -> Drivers:
        random.seed(f"{scenario_name}-{seed}-{t.isoformat()}")
        
        # Base values per scenario §8.1
        if scenario_name == "barcelona-humid":
            base_temp = 22.0
            base_humidity = 0.78
            pm25 = 15.0 + 10.0 * random.random()
        elif scenario_name == "phoenix-dry":
            base_temp = 35.0
            base_humidity = 0.18
            pm25 = 5.0 + 5.0 * random.random()
        else: # stressed
            base_temp = 25.0
            base_humidity = 0.65
            pm25 = 40.0 + 20.0 * random.random()

        # Add some time-of-day variation to temp
        hour = t.hour + t.minute / 60.0
        temp_var = 5.0 * (1.0 - abs(hour - 14.0) / 12.0)
        
        # operator_shift §6.1
        if t.weekday() >= 5:
            shift = "weekend"
        elif 6 <= t.hour < 18:
            shift = "day"
        else:
            shift = "night"

        # cumulative hours/cycles (this should be tracked by the loop, but for the mock it's simpler)
        # We'll assume the loop starts at a fixed time
        start_time = datetime(2026, 4, 25, 8, 0, 0)
        elapsed_hours = (t - start_time).total_seconds() / 3600.0
        
        return Drivers(
            temp_C=base_temp + temp_var,
            humidity=base_humidity,
            pm25=pm25,
            psd_d50=20.0 + (5.0 if scenario_name == "stressed" else 0.0),
            voltage_stability=0.95 + 0.05 * random.random(),
            cycles=int(elapsed_hours * 10),
            hours=elapsed_hours,
            maintenance_level={cid: 1.0 for cid in ComponentId},
            operator_shift=shift,
            rng_seed=seed
        )
