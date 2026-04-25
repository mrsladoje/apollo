from datetime import datetime
from typing import Protocol
from engine.contracts import Drivers, ComponentId

class DriverProvider(Protocol):
    def get(self, t: datetime, scenario_name: str, seed: int) -> Drivers:
        ...
