from unittest.mock import patch

from src.backend.schemas import RecommendationRequest, VehicleDiagnosisRequest
from src.backend.services import diagnose_vehicle, get_recommendations


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


@patch("src.backend.services.cached_station_search", return_value=STATIONS)
@patch("src.backend.services.get_current_temperature", return_value=20.0)
def test_auto_mode_recommends_fast(mock_temperature, mock_search):
    result = get_recommendations(
        RecommendationRequest(location="수원시", mode="auto", limit=1)
    )
    assert result.recommended_mode == "fast"
    assert result.stations[0].name == "급속 충전소"


@patch("src.backend.services.search_service_centers")
@patch("src.backend.services.predict_vehicle", return_value={
    "vehicle_id": "EV0001", "status": "normal",
    "prediction": "0", "probability": 0.1,
})
def test_normal_diagnosis_does_not_search_centers(mock_predict, mock_search):
    result = diagnose_vehicle(VehicleDiagnosisRequest(
        vehicle_id="EV0001", location="수원시", brand="Tesla",
    ))

    assert result.vehicle_id == "EV0001"
    assert result.status == "normal"
    assert result.probability == 0.1
    assert result.service_centers == []
    mock_predict.assert_called_once_with("EV0001")
    mock_search.assert_not_called()


@patch(
    "src.backend.services.search_service_centers",
    return_value=[{
        "name": "테슬라 서비스센터", "address": "수원시",
        "phone": "031-123-4567", "link": "https://example.com",
        "brand": "Tesla",
    }],
)
@patch("src.backend.services.predict_vehicle", return_value={
    "vehicle_id": "EV0002", "status": "abnormal",
    "prediction": "1", "probability": 0.8,
})
def test_failure_diagnosis_returns_service_centers(mock_predict, mock_search):
    result = diagnose_vehicle(VehicleDiagnosisRequest(
        vehicle_id="EV0002", location="수원시", brand="Tesla",
    ))

    assert result.status == "abnormal"
    assert result.probability == 0.8
    assert "불량" in result.message
    assert result.service_centers[0].name == "테슬라 서비스센터"
    mock_search.assert_called_once_with("수원시", "Tesla")
