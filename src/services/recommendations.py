"""Compatibility-preserving charging recommendation service."""

from src.apis.temperature import get_current_temperature, recommend_charging_mode
from src.backend.schemas import RecommendationRequest, RecommendationResponse
from src.crawlers.charging_cache import cached_station_search
from src.crawlers.crawler import recommend_stations, search_charging_stations


def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """Return the legacy recommendations response using the existing providers."""
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
