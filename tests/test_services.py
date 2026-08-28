from unittest.mock import patch

from src.backend.schemas import RecommendationRequest
from src.backend.services import get_recommendations


STATIONS = [
    {
        "name": "완속 충전소", "address": "수원시 A", "available": 5,
        "charging": 0, "unknown": 0, "slow_available": 4,
        "fast_available": 1, "detail_url": None,
    },
    {
        "name": "급속 충전소", "address": "수원시 B", "available": 6,
        "charging": 0, "unknown": 0, "slow_available": 1,
        "fast_available": 5, "detail_url": None,
    },
]


@patch("src.services.recommendations.cached_station_search", return_value=STATIONS)
@patch("src.services.recommendations.get_current_temperature", return_value=20.0)
def test_auto_mode_recommends_fast(mock_temperature, mock_search):
    result = get_recommendations(
        RecommendationRequest(location="수원시", mode="auto", limit=1)
    )
    assert result.recommended_mode == "fast"
    assert result.stations[0].name == "급속 충전소"
