from unittest.mock import patch

from fastapi.testclient import TestClient

from src.apis.temperature import TemperatureError
from src.backend.main import app
from src.backend.schemas import VehicleDiagnosisResponse


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["active_model"] == "reviewed-xgb-3.2.0"
    assert body["providers"]["charging"] == "chargecheck"


@patch(
    "src.backend.main.get_recommendations",
    side_effect=TemperatureError("날씨 조회 실패"),
)
def test_temperature_error_returns_bad_gateway(mock_service):
    response = client.post(
        "/api/v1/recommendations",
        json={"location": "수원시", "mode": "auto", "limit": 3},
    )
    assert response.status_code == 502


def test_invalid_mode_returns_validation_error():
    response = client.post(
        "/api/v1/recommendations",
        json={"location": "수원시", "mode": "invalid", "limit": 3},
    )
    assert response.status_code == 422


@patch(
    "src.backend.main.diagnose_vehicle",
    return_value=VehicleDiagnosisResponse(
        vehicle_id="EV0001", brand="Tesla", status="normal",
        prediction="0", probability=0.1, message="정상입니다.",
        service_centers=[],
    ),
)
def test_vehicle_diagnosis_endpoint_needs_only_vehicle_id(mock_service):
    response = client.post(
        "/api/v1/diagnoses",
        json={"vehicle_id": "EV0001", "location": "수원시", "brand": "Tesla"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "normal"


def test_empty_vehicle_id_returns_validation_error():
    response = client.post(
        "/api/v1/diagnoses",
        json={"vehicle_id": "", "location": "수원시", "brand": "Tesla"},
    )
    assert response.status_code == 422


@patch(
    "src.backend.main.diagnose_vehicle",
    side_effect=FileNotFoundError("차량 모델 파일이 없습니다"),
)
def test_missing_model_returns_service_unavailable(mock_service):
    response = client.post(
        "/api/v1/diagnoses",
        json={"vehicle_id": "EV0002", "location": "서울", "brand": "Nissan"},
    )
    assert response.status_code == 503
