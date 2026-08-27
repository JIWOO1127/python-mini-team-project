from datetime import datetime, timedelta, timezone

from src.crawlers import charging_cache


STATIONS = [{
    "name": "충전소",
    "address": "수원시",
    "available": 3,
    "slow_available": 2,
    "fast_available": 1,
    "detail_url": None,
}]


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(charging_cache, "CACHE_FILE", tmp_path / "cache.csv")
    now = datetime.now(timezone.utc)
    charging_cache.save_charging_cache(" 수원시 ", STATIONS, now=now)
    assert charging_cache.load_charging_cache("수원시", now=now) == STATIONS


def test_expired_cache_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(charging_cache, "CACHE_FILE", tmp_path / "cache.csv")
    now = datetime.now(timezone.utc)
    charging_cache.save_charging_cache("수원시", STATIONS, now=now)
    later = now + timedelta(minutes=11)
    assert charging_cache.load_charging_cache("수원시", now=later) == []
