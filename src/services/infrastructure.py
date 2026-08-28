from __future__ import annotations

import math

from src.providers.registry import charging_provider, geocoder, service_center_provider, settings, weather


def _distance_km(origin, station: dict) -> float | None:
    if station.get("latitude") is None or station.get("longitude") is None:
        return None
    radius = 6371.0
    lat1, lon1 = math.radians(origin.latitude), math.radians(origin.longitude)
    lat2, lon2 = math.radians(float(station["latitude"])), math.radians(float(station["longitude"]))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return round(radius * 2 * math.asin(math.sqrt(a)), 2)


def charging_stations(address: str, mode: str = "auto", limit: int = 3) -> dict:
    coordinates = geocoder().geocode(address)
    temperature = weather().current_temperature(coordinates)
    threshold = float(settings()["temperature_policy"]["slow_at_or_above_celsius"])
    recommended_mode = "slow" if temperature >= threshold else "fast"
    selected_mode = recommended_mode if mode == "auto" else mode
    stations = charging_provider().search(address)
    availability_key = "slow_available" if selected_mode == "slow" else "fast_available"
    stations = [station for station in stations if (station.get(availability_key) or 0) > 0]
    stations.sort(key=lambda station: station.get(availability_key) or 0, reverse=True)
    return {
        "address": address, "coordinates": {"latitude": coordinates.latitude, "longitude": coordinates.longitude},
        "temperature_celsius": temperature, "requested_mode": mode, "recommended_mode": recommended_mode,
        "stations": stations[:limit], "source": charging_provider().name,
    }


def service_centers(address: str, brand: str, limit: int = 5) -> dict:
    origin = geocoder().geocode(address)
    centers = service_center_provider().search(address, brand, limit)
    for center in centers:
        center["distance_km"] = _distance_km(origin, center)
    centers.sort(key=lambda center: (center["distance_km"] is None, center["distance_km"] or float("inf")))
    return {"address": address, "brand": brand, "centers": centers, "source": service_center_provider().name}
