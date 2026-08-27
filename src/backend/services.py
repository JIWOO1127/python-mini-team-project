"""Application services for charging recommendations and diagnosis."""

from src.apis.temperature import get_current_temperature, recommend_charging_mode
from src.backend.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    VehicleDiagnosisRequest,
    VehicleDiagnosisResponse,
)
from src.crawlers.charging_cache import cached_station_search
from src.crawlers.crawler import recommend_stations, search_charging_stations
from src.crawlers.crawler2 import search_service_centers
from src.ml.predictor import predict_vehicle


def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    temperature = get_current_temperature(request.location)
    selected_mode = (
        recommend_charging_mode(temperature)
        if request.mode == "auto"
        else request.mode
    )
    stations = cached_station_search(request.location, search_charging_stations)
    recommendations = recommend_stations(
        stations, mode=selected_mode, limit=request.limit,
    )
    return RecommendationResponse(
        location=request.location,
        temperature=temperature,
        requested_mode=request.mode,
        recommended_mode=selected_mode,
        stations=recommendations,
    )


def diagnose_vehicle(request: VehicleDiagnosisRequest) -> VehicleDiagnosisResponse:
    diagnosis = predict_vehicle(request.vehicle_id)
    centers = []
    if diagnosis["status"] == "abnormal":
        centers = search_service_centers(request.location, request.brand)

    messages = {
        "normal": "차량 배터리가 정상으로 판정되었습니다.",
        "abnormal": "배터리 불량 가능성이 감지되어 주변 서비스센터를 검색했습니다.",
        "unknown": "모델 출력 규칙을 해석할 수 없어 판정을 보류했습니다.",
    }
    return VehicleDiagnosisResponse(
        vehicle_id=diagnosis["vehicle_id"],
        brand=request.brand,
        status=diagnosis["status"],
        prediction=diagnosis["prediction"],
        probability=diagnosis["probability"],
        message=messages[diagnosis["status"]],
        service_centers=centers,
    )
