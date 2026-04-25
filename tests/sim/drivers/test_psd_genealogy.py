from __future__ import annotations

from sim.drivers.composite import _psd_d50


def test_psd_genealogy_drifts_with_powder_age():
    assert _psd_d50("phoenix-dry", elapsed_hours=10.0) > _psd_d50(
        "phoenix-dry", elapsed_hours=0.0
    )


def test_stressed_psd_degrades_twice_as_fast():
    normal_delta = _psd_d50("barcelona-humid", 10.0) - _psd_d50(
        "barcelona-humid", 0.0
    )
    stressed_delta = _psd_d50("stressed", 10.0) - _psd_d50("stressed", 0.0)
    assert stressed_delta == 2.0 * normal_delta
