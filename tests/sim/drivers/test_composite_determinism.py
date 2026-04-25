"""§6.4 — same ``(t, scenario, seed)`` ⇒ bit-identical Drivers and the
provider does not pollute Python's global random state.
"""

from __future__ import annotations

import random
from datetime import datetime

from sim.drivers.composite import CompositeDriverProvider


def _drivers_at(scenario: str = "stressed", seed: int = 42):
    return CompositeDriverProvider().get(
        datetime(2026, 4, 25, 12, 0, 0), scenario, seed
    )


def test_composite_provider_is_deterministic():
    a = _drivers_at()
    b = _drivers_at()
    assert a == b


def test_composite_provider_does_not_touch_global_random():
    random.seed(123)
    before = random.random()

    random.seed(123)
    _drivers_at()  # would have advanced global random in the old impl
    after = random.random()
    assert after == before


def test_operator_shift_is_calendar_correct():
    cdp = CompositeDriverProvider()
    monday_3am = datetime(2026, 4, 27, 3, 0, 0)
    saturday_2pm = datetime(2026, 4, 25, 14, 0, 0)
    weekday_noon = datetime(2026, 4, 28, 12, 0, 0)

    assert cdp.get(monday_3am, "stressed", 0).operator_shift == "night"
    assert cdp.get(saturday_2pm, "stressed", 0).operator_shift == "weekend"
    assert cdp.get(weekday_noon, "stressed", 0).operator_shift == "day"
