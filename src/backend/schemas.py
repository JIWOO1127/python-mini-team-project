"""Stable API schemas. Provider-specific fields do not leak past this layer."""

from typing import Literal

from pydantic import BaseModel, Field


ChargingMode = Literal["auto", "slow", "fast"]
VehicleBrand = Literal["Tesla", "Volkswagen", "Nissan"]


class RecommendationRequest(BaseModel):
    location: str = Field(min_length=1)
    mode: ChargingMode = "auto"
    limit: int = Field(default=3, ge=1, le=10)


class ChargingStationRequest(BaseModel):
    address: str = Field(min_length=1)
    mode: ChargingMode = "auto"
    limit: int = Field(default=3, ge=1, le=10)


class ServiceCenterRequest(BaseModel):
    address: str = Field(min_length=1)
    brand: VehicleBrand
    limit: int = Field(default=5, ge=1, le=20)


class VehicleDiagnosisRequest(BaseModel):
    vehicle_id: str = Field(min_length=1)
    address: str | None = Field(default=None, min_length=1)
    # Retained for the original desktop client during migration.
    location: str | None = Field(default=None, min_length=1)
    brand: VehicleBrand | None = None


class StationResponse(BaseModel):
    name: str
    address: str
    available: int | None = None
    slow_available: int | None = None
    fast_available: int | None = None
    detail_url: str | None = None
    source: str | None = None


class RecommendationResponse(BaseModel):
    location: str
    temperature: float
    requested_mode: ChargingMode
    recommended_mode: Literal["slow", "fast"]
    stations: list[StationResponse]


class ServiceCenterResponse(BaseModel):
    name: str
    address: str
    phone: str
    link: str | None = None
    detail_url: str | None = None
    brand: str
    distance_km: float | None = None
    source: str | None = None


class VehicleDiagnosisResponse(BaseModel):
    vehicle_id: str
    brand: str
    status: Literal["normal", "abnormal", "unknown"]
    prediction: str
    probability: float | None = Field(default=None, ge=0, le=1)
    vehicle_summary: dict = Field(default_factory=dict)
    risk_factors: list[dict] = Field(default_factory=list)
    message: str = ""
    service_centers: list[ServiceCenterResponse] = Field(default_factory=list)
