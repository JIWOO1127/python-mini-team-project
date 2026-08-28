from __future__ import annotations

from datetime import datetime, timezone

from src.crawlers.charging_cache import cached_station_search
from src.crawlers.crawler import ChargeCheckError, search_charging_stations
from src.providers.geocoding.kakao import ProviderError


class ChargeCheckProvider:
    name = "chargecheck"

    def search(self, address: str) -> list[dict]:
        try:
            stations = cached_station_search(address, search_charging_stations)
        except ChargeCheckError as exc:
            raise ProviderError(str(exc)) from exc
        fetched_at = datetime.now(timezone.utc).isoformat()
        return [
            {
                "name": station.get("name", ""),
                "address": station.get("address", ""),
                "latitude": None,
                "longitude": None,
                "distance_km": None,
                "phone": None,
                "available": station.get("available"),
                "slow_available": station.get("slow_available"),
                "fast_available": station.get("fast_available"),
                "detail_url": station.get("detail_url"),
                "source": self.name,
                "fetched_at": fetched_at,
                "cached": False,
            }
            for station in stations
        ]
