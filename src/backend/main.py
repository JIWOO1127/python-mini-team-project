"""FastAPI entry point for the extensible EV assistant."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from src.backend.schemas import (
    ChargingStationRequest,
    RecommendationRequest,
    RecommendationResponse,
    ServiceCenterRequest,
    VehicleDiagnosisRequest,
    VehicleDiagnosisResponse,
)
from src.backend.services import get_recommendations
from src.providers.geocoding.kakao import ProviderError
from src.providers.registry import settings
from src.services.diagnosis import dashboard, diagnose
from src.services.infrastructure import charging_stations, service_centers


app = FastAPI(title="EV Battery & Infrastructure Assistant", version="2.0.0")


@app.get("/")
def index():
    return {
        "service": "EV Battery & Infrastructure Assistant API",
        "desktop_ui": "python -m src.ui",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_model": settings()["active_model"],
        "providers": {
            "geocoding": "kakao-local",
            "weather": "kma-ultra-short-term",
            "charging": "chargecheck",
            "service_centers": "official-manufacturer-catalog",
        },
    }


@app.get("/api/v1/dashboard")
def get_dashboard():
    try:
        return dashboard()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/diagnoses", response_model=VehicleDiagnosisResponse)
def vehicle_diagnosis(request: VehicleDiagnosisRequest) -> VehicleDiagnosisResponse:
    try:
        return diagnose_vehicle(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (LookupError, ValueError, TypeError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def diagnose_vehicle(request: VehicleDiagnosisRequest) -> VehicleDiagnosisResponse:
    result = diagnose(request.vehicle_id)
    result["message"] = "테스트 차량 데이터와 현재 활성 모델로 분석한 참고용 결과입니다."
    return VehicleDiagnosisResponse(**result)


@app.post("/api/v1/charging-stations")
def charging_stations_endpoint(request: ChargingStationRequest):
    try:
        return charging_stations(request.address, request.mode, request.limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/service-centers")
def service_centers_endpoint(request: ServiceCenterRequest):
    try:
        return service_centers(request.address, request.brand, request.limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
def recommendations(request: RecommendationRequest) -> RecommendationResponse:
    try:
        return get_recommendations(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
