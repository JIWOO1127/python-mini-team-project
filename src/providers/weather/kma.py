from __future__ import annotations

from src.apis.temperature import TemperatureError, convert_to_grid, fetch_temperature
from src.contracts.providers import Coordinates
from src.providers.geocoding.kakao import ProviderError


class KmaWeatherProvider:
    name = "kma-ultra-short-term"

    def current_temperature(self, coordinates: Coordinates) -> float:
        try:
            nx, ny = convert_to_grid(coordinates.latitude, coordinates.longitude)
            return fetch_temperature(nx, ny)
        except TemperatureError as exc:
            raise ProviderError(str(exc)) from exc
