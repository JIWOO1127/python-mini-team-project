from unittest.mock import patch

from src.contracts.providers import Coordinates
from src.services.infrastructure import charging_stations, service_centers


class FakeGeocoder:
    def geocode(self, address):
        return Coordinates(37.5, 127.0)


class FakeWeather:
    def current_temperature(self, coordinates):
        return 30.0


class FakeCharging:
    name = "fake-charging"

    def search(self, address):
        return [
            {"name": "완속", "slow_available": 2, "fast_available": 0},
            {"name": "급속", "slow_available": 0, "fast_available": 3},
        ]


class FakeCenters:
    name = "fake-centers"

    def search(self, address, brand, limit):
        return [{"name": "센터", "address": address, "latitude": 37.51, "longitude": 127.01}]


@patch("src.services.infrastructure.settings", return_value={"temperature_policy": {"slow_at_or_above_celsius": 30.0}})
@patch("src.services.infrastructure.charging_provider", return_value=FakeCharging())
@patch("src.services.infrastructure.weather", return_value=FakeWeather())
@patch("src.services.infrastructure.geocoder", return_value=FakeGeocoder())
def test_temperature_boundary_selects_slow(mock_geocoder, mock_weather, mock_charging, mock_settings):
    result = charging_stations("서울", "auto")
    assert result["recommended_mode"] == "slow"
    assert result["stations"][0]["name"] == "완속"


@patch("src.services.infrastructure.service_center_provider", return_value=FakeCenters())
@patch("src.services.infrastructure.geocoder", return_value=FakeGeocoder())
def test_center_response_is_normalized_with_distance(mock_geocoder, mock_centers):
    result = service_centers("서울", "Tesla")
    assert result["source"] == "fake-centers"
    assert result["centers"][0]["distance_km"] is not None
