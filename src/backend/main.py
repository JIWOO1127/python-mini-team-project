"""FastAPI entry point for the EV Charging Assistant backend."""

from fastapi import FastAPI, HTTPException

from src.apis.temperature import TemperatureError
from src.backend.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    VehicleDiagnosisRequest,
    VehicleDiagnosisResponse,
)
from src.backend.services import diagnose_vehicle, get_recommendations
from src.crawlers.crawler import ChargeCheckError


app = FastAPI(
    title="EV Charging Assistant API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/api/v1/recommendations",
    response_model=RecommendationResponse,
)
def recommendations(
    request: RecommendationRequest,
) -> RecommendationResponse:
    try:
        return get_recommendations(request)
    except (TemperatureError, ChargeCheckError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(
    "/api/v1/diagnoses",
    response_model=VehicleDiagnosisResponse,
)
def vehicle_diagnosis(
    request: VehicleDiagnosisRequest,
) -> VehicleDiagnosisResponse:
    try:
        return diagnose_vehicle(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (LookupError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
