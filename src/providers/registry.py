from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.providers.charging import ChargeCheckProvider
from src.providers.geocoding import KakaoGeocodingProvider
from src.providers.service_centers import OfficialServiceCenterProvider
from src.providers.weather import KmaWeatherProvider


ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def settings() -> dict:
    return json.loads((ROOT / "config" / "providers.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def geocoder():
    return KakaoGeocodingProvider()


@lru_cache(maxsize=1)
def weather():
    return KmaWeatherProvider()


@lru_cache(maxsize=1)
def charging_provider():
    return ChargeCheckProvider()


@lru_cache(maxsize=1)
def service_center_provider():
    return OfficialServiceCenterProvider()
