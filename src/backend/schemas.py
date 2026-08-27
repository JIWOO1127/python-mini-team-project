"""Request and response schemas for the charging recommendation API."""

from typing import Literal

from pydantic import BaseModel, Field


ChargingMode = Literal["auto", "slow", "fast"]
VehicleBrand = Literal["Tesla", "Volkswagen", "Nissan"]


class RecommendationRequest(BaseModel):
    location: str = Field(min_length=1)
    mode: ChargingMode = "auto"
    limit: int = Field(default=3, ge=1, le=10)


class StationResponse(BaseModel):
    name: str
    address: str
    available: int | None = None
    slow_available: int | None = None
    fast_available: int | None = None


class RecommendationResponse(BaseModel):
    location: str
    temperature: float
    requested_mode: ChargingMode
    recommended_mode: Literal["slow", "fast"]
    stations: list[StationResponse]


class VehicleDiagnosisRequest(BaseModel):
    vehicle_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    brand: VehicleBrand


class ServiceCenterResponse(BaseModel):
    name: str
    address: str
    phone: str
    link: str
    brand: VehicleBrand


class VehicleDiagnosisResponse(BaseModel):
    vehicle_id: str
    brand: VehicleBrand
    status: Literal["normal", "abnormal", "unknown"]
    prediction: str
    probability: float | None = Field(default=None, ge=0, le=1)
    message: str
    service_centers: list[ServiceCenterResponse]
