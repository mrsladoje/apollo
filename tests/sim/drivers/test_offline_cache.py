from __future__ import annotations

from pathlib import Path

from sim.drivers import cache_all as cache_mod


def test_offline_cache_writes_all_demo_csvs(tmp_path, monkeypatch):
    weather_dir = tmp_path / "weather"
    air_dir = tmp_path / "air"
    monkeypatch.setattr(cache_mod, "WEATHER_DIR", str(weather_dir))
    monkeypatch.setattr(cache_mod, "AIR_DIR", str(air_dir))

    artifacts = cache_mod.cache_all(force=True)

    assert set(artifacts) == {
        "weather:barcelona",
        "air:barcelona",
        "weather:phoenix",
        "air:phoenix",
    }
    for path in artifacts.values():
        assert Path(path).exists()


def test_offline_cache_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "WEATHER_DIR", str(tmp_path / "weather"))
    monkeypatch.setattr(cache_mod, "AIR_DIR", str(tmp_path / "air"))
    first = cache_mod.cache_all(force=True)
    first_bytes = {k: open(v, "rb").read() for k, v in first.items()}
    second = cache_mod.cache_all(force=True)
    second_bytes = {k: open(v, "rb").read() for k, v in second.items()}
    assert first_bytes == second_bytes
