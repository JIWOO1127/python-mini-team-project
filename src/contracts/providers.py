from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


class GeocodingProvider(Protocol):
    name: str

    def geocode(self, address: str) -> Coordinates: ...


class WeatherProvider(Protocol):
    name: str

    def current_temperature(self, coordinates: Coordinates) -> float: ...


class ChargingStationProvider(Protocol):
    name: str

    def search(self, address: str) -> list[dict]: ...


class ServiceCenterProvider(Protocol):
    name: str

    def search(self, address: str, brand: str, limit: int = 10) -> list[dict]: ...
